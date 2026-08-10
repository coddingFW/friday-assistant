"""Serviço de conversa — orquestra RAG + LLM em um turno (caso de uso central).

É o ponto onde a regra de negócio do diálogo vive: dado o texto do usuário,
opcionalmente busca contexto na web (RAG), monta as mensagens e transmite a
resposta do LLM em streaming, emitindo eventos de domínio ao longo do caminho.
Degrada graciosamente: se a busca falhar, responde sem contexto.
"""

from __future__ import annotations

import asyncio
import contextlib
import random
from collections.abc import Sequence
from typing import AsyncIterator

from backend.brain.events import (
    AudioReady,
    ConversationEvent,
    GenerationFailed,
    SourceRef,
    SourcesGathered,
    StatusChanged,
    TokenGenerated,
    TurnCompleted,
)
from backend.brain.ports import ChatMessage, LLMProvider
from backend.config.settings import Settings
from backend.rag.service import RagService
from backend.tts.ports import SpeechAudio, TTSProvider
from backend.tts.text import to_speech_text
from backend.utils.errors import LLMError, RagError, TTSError
from backend.utils.logging import get_logger

logger = get_logger(__name__)

#: Sentinela que marca o fim do fluxo de eventos do produtor.
_DONE = object()


class ConversationService:
    """Caso de uso: transformar uma pergunta em uma resposta (RAG + voz opcionais)."""

    def __init__(
        self,
        llm: LLMProvider,
        rag: RagService,
        settings: Settings,
        tts: TTSProvider | None = None,
    ) -> None:
        self._llm = llm
        self._rag = rag
        self._settings = settings
        self._tts = tts
        # Cache de frases-ponte já sintetizadas (fala durante a busca) e a última
        # usada, para não repetir a mesma duas vezes seguidas (menos robótico).
        self._filler_cache: dict[str, SpeechAudio] = {}
        self._last_filler: str | None = None

    async def run(
        self,
        query: str,
        *,
        model: str | None = None,
        history: Sequence[ChatMessage] = (),
    ) -> AsyncIterator[ConversationEvent]:
        """Processa um turno e emite eventos de domínio em streaming.

        ``history`` traz os turnos anteriores (user/assistant) da mesma conversa,
        dando contexto multi-turno ao LLM; vazio = turno isolado (sem memória).

        O turno real roda num produtor; este consumidor repassa os eventos e, nas
        esperas antes de a resposta começar (busca e/ou "pensar" do LLM), preenche
        o silêncio com frases-ponte faladas: uma imediata ao entrar na busca e
        outras a cada ``tts_filler_interval`` segundos — conversa menos robótica.
        """
        queue: asyncio.Queue[object] = asyncio.Queue()
        producer = asyncio.create_task(self._produce(query, model, history, queue))
        interval = self._settings.tts_filler_interval
        responding = False
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=interval)
                except asyncio.TimeoutError:
                    # Espera longa e ainda sem resposta: fala outra frase-ponte.
                    if not responding:
                        filler = await self._make_filler()
                        if filler is not None:
                            yield filler
                    continue
                if item is _DONE:
                    break
                event: ConversationEvent = item  # type: ignore[assignment]
                yield event
                if isinstance(event, StatusChanged):
                    if event.state == "responding":
                        responding = True
                    elif event.state == "searching":
                        # Frase-ponte imediata ao começar a busca.
                        filler = await self._make_filler()
                        if filler is not None:
                            yield filler
        finally:
            if not producer.done():
                producer.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await producer

    async def _produce(
        self,
        query: str,
        model: str | None,
        history: Sequence[ChatMessage],
        queue: asyncio.Queue[object],
    ) -> None:
        """Roda o turno de domínio e empilha os eventos na fila para o consumidor."""
        try:
            async for event in self._turn_events(query, model=model, history=history):
                await queue.put(event)
        except Exception as exc:  # noqa: BLE001 - isola falha inesperada do produtor
            logger.error("conversation_produce_error", error=str(exc))
        finally:
            await queue.put(_DONE)

    async def _turn_events(
        self,
        query: str,
        *,
        model: str | None,
        history: Sequence[ChatMessage],
    ) -> AsyncIterator[ConversationEvent]:
        """Eventos de domínio de um turno (RAG + LLM + voz), sem frases-ponte.

        Observação: nada de `yield` em bloco `finally`. Se o gerador for fechado no
        meio (cancelamento do produtor), o Python lança GeneratorExit no ponto do
        yield; emitir durante a limpeza geraria "async generator ignored
        GeneratorExit". O estado "idle" é emitido nos caminhos normais/erro.
        """
        yield StatusChanged(state="thinking")

        results = []
        if self._settings.rag_enabled:
            yield StatusChanged(state="searching")
            try:
                results = await self._rag.retrieve(query)
                yield SourcesGathered(
                    sources=[SourceRef(title=r.title, url=r.url) for r in results]
                )
            except RagError as exc:
                # Degradação graciosa: segue sem contexto de busca.
                logger.warning("rag_retrieve_failed", error=str(exc))
                results = []

        messages = self._rag.build_messages(query, results, history)

        answer_parts: list[str] = []
        try:
            responding = False
            async for token in self._llm.stream_chat(messages, model=model):
                if not responding:
                    yield StatusChanged(state="responding")
                    responding = True
                answer_parts.append(token)
                yield TokenGenerated(text=token)
        except LLMError as exc:
            logger.warning("conversation_llm_error", error=str(exc))
            yield GenerationFailed(message=str(exc))
            yield StatusChanged(state="idle")
            return

        audio = await self._synthesize("".join(answer_parts))
        if audio is not None:
            yield audio

        yield TurnCompleted()
        yield StatusChanged(state="idle")

    async def _make_filler(self) -> AudioReady | None:
        """Sintetiza (e cacheia) uma frase-ponte curta para tocar durante a busca.

        Degrada graciosamente: sem TTS, desativado ou em caso de falha, apenas
        omite a frase — a busca segue normalmente.
        """
        settings = self._settings
        if not (settings.tts_enabled and self._tts is not None):
            return None
        if not settings.tts_fillers_enabled or not settings.tts_filler_phrases:
            return None
        phrase = self._pick_filler_phrase(settings.tts_filler_phrases)
        speech = self._filler_cache.get(phrase)
        if speech is None:
            try:
                speech = await self._tts.synthesize(phrase)
            except TTSError as exc:
                logger.warning("conversation_filler_tts_error", error=str(exc))
                return None
            self._filler_cache[phrase] = speech
        return AudioReady(data=speech.data, mime=speech.mime)

    def _pick_filler_phrase(self, phrases: Sequence[str]) -> str:
        """Escolhe uma frase-ponte ao acaso, evitando repetir a última usada."""
        candidates = [p for p in phrases if p != self._last_filler] or list(phrases)
        phrase = random.choice(candidates)
        self._last_filler = phrase
        return phrase

    async def _synthesize(self, answer: str) -> AudioReady | None:
        """Sintetiza a voz da resposta, se o TTS estiver ativo.

        Degrada graciosamente: qualquer falha de TTS apenas omite o áudio, sem
        interromper o turno (a resposta em texto já foi entregue).
        """
        if not self._settings.tts_enabled or self._tts is None:
            return None
        spoken = to_speech_text(answer)
        if not spoken:
            return None
        logger.info("tts_spoken_preview", text=spoken[:200])
        try:
            speech = await self._tts.synthesize(spoken)
        except TTSError as exc:
            logger.warning("conversation_tts_error", error=str(exc))
            return None
        return AudioReady(data=speech.data, mime=speech.mime)
