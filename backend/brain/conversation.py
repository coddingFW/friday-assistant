"""Serviço de conversa — orquestra RAG + LLM em um turno (caso de uso central).

É o ponto onde a regra de negócio do diálogo vive: dado o texto do usuário,
opcionalmente busca contexto na web (RAG), monta as mensagens e transmite a
resposta do LLM em streaming, emitindo eventos de domínio ao longo do caminho.
Degrada graciosamente: se a busca falhar, responde sem contexto.
"""

from __future__ import annotations

from typing import AsyncIterator

from backend.brain.events import (
    ConversationEvent,
    GenerationFailed,
    SourceRef,
    SourcesGathered,
    StatusChanged,
    TokenGenerated,
    TurnCompleted,
)
from backend.brain.ports import LLMProvider
from backend.config.settings import Settings
from backend.rag.service import RagService
from backend.utils.errors import LLMError, RagError
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class ConversationService:
    """Caso de uso: transformar uma pergunta em uma resposta (com RAG opcional)."""

    def __init__(
        self, llm: LLMProvider, rag: RagService, settings: Settings
    ) -> None:
        self._llm = llm
        self._rag = rag
        self._settings = settings

    async def run(
        self, query: str, *, model: str | None = None
    ) -> AsyncIterator[ConversationEvent]:
        """Processa um turno e emite eventos de domínio em streaming."""
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

        messages = self._rag.build_messages(query, results)

        # Observação: nada de `yield` em bloco `finally`. Se o consumidor fechar
        # este gerador no meio do streaming (cliente desconectou), o Python lança
        # GeneratorExit no ponto do yield; tentar emitir durante a limpeza gera
        # "async generator ignored GeneratorExit". O estado "idle" é emitido nos
        # caminhos normais/erro abaixo, nunca em finally.
        try:
            responding = False
            async for token in self._llm.stream_chat(messages, model=model):
                if not responding:
                    yield StatusChanged(state="responding")
                    responding = True
                yield TokenGenerated(text=token)
        except LLMError as exc:
            logger.warning("conversation_llm_error", error=str(exc))
            yield GenerationFailed(message=str(exc))
            yield StatusChanged(state="idle")
            return

        yield TurnCompleted()
        yield StatusChanged(state="idle")
