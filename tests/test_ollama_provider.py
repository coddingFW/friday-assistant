"""Testes do adapter OllamaProvider usando transporte HTTP mockado.

Não requerem um Ollama real: usam ``httpx.MockTransport`` para simular as
respostas do serviço, exercitando o parsing de NDJSON e o tratamento de erros.
"""

from __future__ import annotations

import json

import httpx
import pytest

from backend.brain.providers.ollama_provider import OllamaProvider
from backend.brain.ports import ChatMessage
from backend.utils.errors import LLMUnavailableError


def _make_provider(handler: httpx.MockTransport) -> OllamaProvider:
    client = httpx.AsyncClient(transport=handler, base_url="http://ollama.test")
    return OllamaProvider(client=client, default_model="llama3.1:8b")


async def test_stream_chat_parses_ndjson() -> None:
    """Deve emitir apenas o conteúdo textual de cada fragmento NDJSON."""
    lines = [
        json.dumps({"message": {"content": "Oi"}, "done": False}),
        json.dumps({"message": {"content": " Juan"}, "done": False}),
        json.dumps({"message": {"content": "!"}, "done": True}),
    ]
    body = "\n".join(lines)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(200, text=body)

    provider = _make_provider(httpx.MockTransport(handler))
    tokens = [
        t async for t in provider.stream_chat([ChatMessage(role="user", content="oi")])
    ]
    assert "".join(tokens) == "Oi Juan!"


async def test_stream_chat_uses_override_model() -> None:
    """O modelo passado na chamada deve sobrescrever o default no payload."""
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["model"] = json.loads(request.content)["model"]
        return httpx.Response(
            200, text=json.dumps({"message": {"content": "ok"}, "done": True})
        )

    provider = _make_provider(httpx.MockTransport(handler))
    _ = [
        t
        async for t in provider.stream_chat(
            [ChatMessage(role="user", content="oi")], model="qwen3"
        )
    ]
    assert captured["model"] == "qwen3"


async def test_stream_chat_raises_when_unreachable() -> None:
    """Erro de conexão deve virar LLMUnavailableError (exceção do domínio)."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = _make_provider(httpx.MockTransport(handler))
    with pytest.raises(LLMUnavailableError):
        _ = [
            t
            async for t in provider.stream_chat(
                [ChatMessage(role="user", content="oi")]
            )
        ]


async def test_stream_chat_includes_images_when_present() -> None:
    """Mensagens com imagens (multimodal) devem incluir 'images' no payload."""
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200, text=json.dumps({"message": {"content": "ok"}, "done": True})
        )

    provider = _make_provider(httpx.MockTransport(handler))
    message = ChatMessage(role="user", content="o que é isto?", images=("BASE64==",))
    _ = [t async for t in provider.stream_chat([message])]

    msg = captured["messages"][0]  # type: ignore[index]
    assert msg["images"] == ["BASE64=="]


async def test_stream_chat_omits_images_for_text_only() -> None:
    """Conversa somente-texto não deve carregar a chave 'images'."""
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200, text=json.dumps({"message": {"content": "ok"}, "done": True})
        )

    provider = _make_provider(httpx.MockTransport(handler))
    _ = [t async for t in provider.stream_chat([ChatMessage(role="user", content="oi")])]
    assert "images" not in captured["messages"][0]  # type: ignore[index]


async def test_list_models() -> None:
    """list_models deve extrair os nomes do payload de /api/tags."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(
            200,
            json={"models": [{"name": "llama3.1:8b"}, {"name": "qwen3"}]},
        )

    provider = _make_provider(httpx.MockTransport(handler))
    assert await provider.list_models() == ["llama3.1:8b", "qwen3"]


async def test_warmup_true_and_false() -> None:
    """warmup deve retornar True em sucesso e False (sem lançar) em falha."""

    def ok_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/generate"
        assert json.loads(request.content)["prompt"] == ""
        return httpx.Response(200, json={"done": True})

    def fail_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    assert await _make_provider(httpx.MockTransport(ok_handler)).warmup() is True
    assert await _make_provider(httpx.MockTransport(fail_handler)).warmup() is False


async def test_health_true_and_false() -> None:
    """health deve refletir a acessibilidade do serviço."""

    def ok_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"version": "0.1.0"})

    def fail_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    assert await _make_provider(httpx.MockTransport(ok_handler)).health() is True
    assert await _make_provider(httpx.MockTransport(fail_handler)).health() is False
