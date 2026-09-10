"""Testes do ConversationService (orquestração RAG + LLM)."""

from __future__ import annotations

import asyncio

from backend.brain.conversation import ConversationService
from backend.config.settings import Settings
from backend.rag.service import RagService
from backend.brain.events import (
    AudioReady,
    GenerationFailed,
    SourcesGathered,
    StatusChanged,
    TokenGenerated,
    TurnCompleted,
)
from backend.brain.ports import ChatMessage
from backend.utils.errors import LLMError
from tests.conftest import (
    FakeLLMProvider,
    FakeSearchProvider,
    FakeTTSProvider,
    build_conversation_service,
)


async def _collect(service, query: str) -> list:
    return [event async for event in service.run(query)]


async def test_run_emits_full_sequence_with_rag() -> None:
    """Deve emitir status + fontes + tokens + conclusão na ordem correta."""
    service = build_conversation_service(llm=FakeLLMProvider(tokens=["x", "y"]))
    events = await _collect(service, "pergunta")

    states = [e.state for e in events if isinstance(e, StatusChanged)]
    assert states == ["thinking", "searching", "responding", "idle"]
    assert any(isinstance(e, SourcesGathered) for e in events)
    tokens = [e.text for e in events if isinstance(e, TokenGenerated)]
    assert tokens == ["x", "y"]
    assert any(isinstance(e, TurnCompleted) for e in events)


async def test_run_without_rag_skips_search() -> None:
    """Com RAG desativado, não há estado 'searching' nem fontes."""
    service = build_conversation_service(rag_enabled=False)
    events = await _collect(service, "pergunta")
    states = [e.state for e in events if isinstance(e, StatusChanged)]
    assert "searching" not in states
    assert not any(isinstance(e, SourcesGathered) for e in events)


async def test_run_degrades_when_search_fails() -> None:
    """Falha de busca não interrompe o turno; segue sem fontes."""
    service = build_conversation_service(
        llm=FakeLLMProvider(tokens=["ok"]), search=FakeSearchProvider(fail=True)
    )
    events = await _collect(service, "pergunta")
    assert not any(isinstance(e, SourcesGathered) for e in events)
    assert any(isinstance(e, TurnCompleted) for e in events)


async def test_run_threads_history_into_llm_messages() -> None:
    """O histórico deve entrar nas mensagens do LLM, antes da pergunta atual."""
    llm = FakeLLMProvider(tokens=["ok"])
    service = build_conversation_service(llm=llm, rag_enabled=False)
    history = [
        ChatMessage(role="user", content="quem foi Viktor Frankl?"),
        ChatMessage(role="assistant", content="Um psiquiatra e filósofo austríaco."),
    ]
    _ = [e async for e in service.run("qual o nome dele?", history=history)]

    sent = llm.calls[-1]
    # 2 system (identidade + comportamento) + 2 de histórico + pergunta atual.
    assert sent[0].role == "system" and sent[1].role == "system"
    assert sent[2:4] == history
    assert sent[-1] == ChatMessage(role="user", content="qual o nome dele?")


async def test_run_speaks_filler_before_searching_when_enabled() -> None:
    """Com TTS + fillers, uma fala-ponte é emitida antes de buscar (sem silêncio)."""
    tts = FakeTTSProvider()
    service = build_conversation_service(
        llm=FakeLLMProvider(tokens=["oi"]),
        tts=tts,
        tts_enabled=True,
        tts_fillers_enabled=True,
    )
    events = await _collect(service, "pergunta")

    audios = [e for e in events if isinstance(e, AudioReady)]
    assert len(audios) == 2  # frase-ponte (busca) + resposta
    idx_filler = events.index(audios[0])
    idx_sources = next(
        i for i, e in enumerate(events) if isinstance(e, SourcesGathered)
    )
    assert idx_filler < idx_sources  # a ponte vem antes das fontes


class _SlowSearch(FakeSearchProvider):
    """Busca falsa que demora, para exercitar as frases-ponte periódicas."""

    async def search(self, query: str, max_results: int):
        await asyncio.sleep(0.25)
        return await super().search(query, max_results)


async def test_run_repeats_fillers_during_slow_search() -> None:
    """Busca demorada gera várias frases-ponte (não só uma) antes das fontes."""
    settings = Settings(
        _env_file=None,
        tts_enabled=True,
        tts_fillers_enabled=True,
        tts_filler_interval=0.05,
    )
    rag = RagService(_SlowSearch(), settings)
    service = ConversationService(
        FakeLLMProvider(tokens=["ok"]), rag, settings, tts=FakeTTSProvider()
    )
    events = [e async for e in service.run("pergunta")]

    idx_sources = next(
        i for i, e in enumerate(events) if isinstance(e, SourcesGathered)
    )
    fillers_before = [e for e in events[:idx_sources] if isinstance(e, AudioReady)]
    assert len(fillers_before) >= 2  # imediata + periódicas durante a espera


def test_filler_phrase_avoids_immediate_repeat() -> None:
    """A frase-ponte nunca repete a mesma duas vezes seguidas."""
    service = build_conversation_service()
    phrases = ["a", "b", "c"]
    prev: str | None = None
    for _ in range(50):
        phrase = service._pick_filler_phrase(phrases)
        assert phrase in phrases
        assert phrase != prev
        prev = phrase


class _FailingLLM(FakeLLMProvider):
    async def stream_chat(self, messages, *, model=None):
        raise LLMError("ollama caiu")
        yield  # pragma: no cover - torna a função um gerador


async def test_run_can_be_closed_midstream_without_error() -> None:
    """Fechar o gerador no meio do streaming não deve levantar (sem yield em finally)."""
    service = build_conversation_service(llm=FakeLLMProvider(tokens=["a"] * 50))
    gen = service.run("pergunta")
    # Consome alguns eventos (thinking, searching, sources, responding, token...).
    for _ in range(5):
        await gen.__anext__()
    # Fechar no meio simula o cliente desconectando: deve encerrar limpo.
    await gen.aclose()


async def test_run_reports_llm_failure() -> None:
    """Erro do LLM deve virar GenerationFailed, e ainda encerrar em idle."""
    service = build_conversation_service(llm=_FailingLLM())
    events = await _collect(service, "pergunta")
    assert any(isinstance(e, GenerationFailed) for e in events)
    assert events[-1] == StatusChanged(state="idle")
