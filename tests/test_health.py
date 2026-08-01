"""Testes dos endpoints REST de saúde e de LLM."""

from __future__ import annotations

import httpx

from tests.conftest import FakeLLMProvider


async def test_health_ok(client: httpx.AsyncClient) -> None:
    """O endpoint de saúde deve reportar status ok e o modelo configurado."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "Friday"
    assert body["llm_reachable"] is True
    assert body["llm_model"] == "llama3.1:8b"


async def test_health_degrades_when_llm_down() -> None:
    """Backend continua 'ok' mesmo com o LLM inacessível (degradação graciosa)."""
    from backend.api.dependencies import get_llm_provider
    from backend.main import create_app

    unreachable = FakeLLMProvider(reachable=False)
    app = create_app()
    app.dependency_overrides[get_llm_provider] = lambda: unreachable
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/api/health")
    assert response.status_code == 200
    assert response.json()["llm_reachable"] is False


async def test_llm_config(client: httpx.AsyncClient) -> None:
    """A config do LLM exposta deve refletir os defaults."""
    response = await client.get("/api/llm/config")
    assert response.status_code == 200
    assert response.json() == {"provider": "ollama", "model": "llama3.1:8b"}


async def test_llm_models(client: httpx.AsyncClient) -> None:
    """A listagem de modelos deve retornar o que o provedor informa."""
    response = await client.get("/api/llm/models")
    assert response.status_code == 200
    assert response.json()["models"] == ["fake-model:latest"]
