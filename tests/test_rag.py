"""Testes da camada de RAG: contexto, serviço e fábrica."""

from __future__ import annotations

import pytest

from backend.config.settings import Settings
from backend.rag.context import build_context
from backend.rag.factory import create_search_provider
from backend.rag.ports import SearchResult
from backend.rag.providers.duckduckgo import DuckDuckGoSearchProvider
from backend.rag.service import RagService
from backend.utils.errors import ProviderConfigError
from tests.conftest import FakeSearchProvider


def test_build_context_empty() -> None:
    """Sem resultados, o contexto é uma string vazia."""
    assert build_context([]) == ""


def test_build_context_formats_sources() -> None:
    """O contexto deve numerar fontes com título, URL e trecho."""
    results = [
        SearchResult(title="A", url="https://a.com", snippet="trecho a"),
        SearchResult(title="B", url="https://b.com", snippet="trecho b"),
    ]
    context = build_context(results)
    assert "[1] A" in context
    assert "https://a.com" in context
    assert "[2] B" in context
    assert "trecho b" in context


async def test_rag_service_retrieve_limits_results() -> None:
    """retrieve deve pedir no máximo rag_max_results ao provedor."""
    settings = Settings(_env_file=None, rag_max_results=2)
    results = [
        SearchResult(title=f"T{i}", url=f"https://e/{i}", snippet="s") for i in range(5)
    ]
    service = RagService(FakeSearchProvider(results=results), settings)
    got = await service.retrieve("q")
    assert len(got) == 2


def test_build_messages_includes_system_context_and_user() -> None:
    """Com resultados, monta system(prompt) + system(contexto) + user."""
    settings = Settings(_env_file=None)
    service = RagService(FakeSearchProvider(), settings)
    results = [SearchResult(title="A", url="https://a.com", snippet="x")]
    messages = service.build_messages("pergunta", results)
    assert [m.role for m in messages] == ["system", "system", "user"]
    assert messages[-1].content == "pergunta"
    assert "https://a.com" in messages[1].content


def test_build_messages_without_results_skips_context() -> None:
    """Sem resultados, não há mensagem de contexto — só system + user."""
    settings = Settings(_env_file=None)
    service = RagService(FakeSearchProvider(), settings)
    messages = service.build_messages("pergunta", [])
    assert [m.role for m in messages] == ["system", "user"]


def test_factory_creates_duckduckgo() -> None:
    """A fábrica deve devolver o adapter DuckDuckGo por padrão."""
    provider = create_search_provider(Settings(_env_file=None))
    assert isinstance(provider, DuckDuckGoSearchProvider)


def test_factory_rejects_unknown_provider() -> None:
    """Provedor de busca desconhecido deve falhar na fábrica."""
    with pytest.raises(ProviderConfigError):
        create_search_provider(Settings(_env_file=None, rag_provider="bing"))
