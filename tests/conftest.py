"""Fixtures compartilhadas dos testes.

Fornece um provedor de LLM falso (implementa a porta :class:`LLMProvider`) e um
cliente HTTP de teste com o provedor injetado via ``dependency_overrides`` — sem
tocar em rede nem no Ollama real.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from backend.api.dependencies import get_llm_provider
from backend.brain.conversation import ConversationService
from backend.brain.ports import ChatMessage
from backend.config.settings import Settings
from backend.main import create_app
from backend.rag.ports import SearchResult
from backend.rag.service import RagService
from backend.tts.ports import SpeechAudio
from backend.utils.errors import SearchUnavailableError, TTSError


class FakeLLMProvider:
    """Provedor de LLM em memória para testes determinísticos."""

    name = "fake"

    def __init__(
        self,
        *,
        reachable: bool = True,
        models: list[str] | None = None,
        tokens: list[str] | None = None,
    ) -> None:
        self._reachable = reachable
        self._models = models if models is not None else ["fake-model:latest"]
        self._tokens = tokens if tokens is not None else ["Olá", ", ", "mundo!"]
        self.calls: list[list[ChatMessage]] = []

    async def health(self) -> bool:
        return self._reachable

    async def list_models(self) -> list[str]:
        return list(self._models)

    async def stream_chat(
        self, messages: list[ChatMessage], *, model: str | None = None
    ) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        for token in self._tokens:
            yield token


class FakeSearchProvider:
    """Provedor de busca falso para testes determinísticos."""

    name = "fake"

    def __init__(
        self, *, results: list[SearchResult] | None = None, fail: bool = False
    ) -> None:
        self._results = (
            results
            if results is not None
            else [SearchResult(title="Título", url="https://ex.com", snippet="trecho")]
        )
        self._fail = fail

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        if self._fail:
            raise SearchUnavailableError("busca indisponível (fake)")
        return self._results[:max_results]


class FakeTTSProvider:
    """Provedor de TTS falso: devolve bytes fixos (ou falha, se configurado)."""

    name = "fake"

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail
        self.calls: list[str] = []

    async def health(self) -> bool:
        return not self._fail

    async def synthesize(self, text: str) -> SpeechAudio:
        self.calls.append(text)
        if self._fail:
            raise TTSError("tts indisponível (fake)")
        return SpeechAudio(data=b"RIFFfake-wav", mime="audio/wav")


def build_conversation_service(
    *,
    llm: FakeLLMProvider | None = None,
    search: FakeSearchProvider | None = None,
    rag_enabled: bool = True,
    tts: FakeTTSProvider | None = None,
    tts_enabled: bool = False,
) -> ConversationService:
    """Monta um ConversationService com dependências falsas para testes."""
    settings = Settings(_env_file=None, rag_enabled=rag_enabled, tts_enabled=tts_enabled)
    rag = RagService(search or FakeSearchProvider(), settings)
    return ConversationService(llm or FakeLLMProvider(), rag, settings, tts=tts)


@pytest.fixture
def fake_provider() -> FakeLLMProvider:
    """Provedor falso padrão (acessível, gera 'Olá, mundo!')."""
    return FakeLLMProvider()


@pytest.fixture
async def client(fake_provider: FakeLLMProvider) -> AsyncIterator[httpx.AsyncClient]:
    """Cliente HTTP de teste com o provedor falso injetado por DI."""
    app = create_app()
    app.state.llm_provider = fake_provider  # usado pelo WebSocket
    app.dependency_overrides[get_llm_provider] = lambda: fake_provider

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as http_client:
        yield http_client

    app.dependency_overrides.clear()
