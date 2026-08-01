"""Testes do ConversationService (orquestração RAG + LLM)."""

from __future__ import annotations

from backend.brain.events import (
    GenerationFailed,
    SourcesGathered,
    StatusChanged,
    TokenGenerated,
    TurnCompleted,
)
from backend.utils.errors import LLMError
from tests.conftest import (
    FakeLLMProvider,
    FakeSearchProvider,
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
