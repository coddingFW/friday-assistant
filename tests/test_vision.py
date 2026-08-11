"""Testes da Fase 8 (visão): imagem no turno, sensor de tela e endpoint REST."""

from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from backend.brain.events import SourcesGathered
from backend.main import create_app
from backend.perception.manager import SensorManager
from backend.perception.modality import Modality
from backend.perception.registry import SensorRegistry
from backend.perception.sensors.screen import SCREEN_DESCRIPTOR, ScreenCaptureSensor
from tests.conftest import FakeLLMProvider, build_conversation_service


async def _collect(service, query, **kw):
    return [event async for event in service.run(query, **kw)]


async def test_run_with_image_uses_vision_model_and_skips_rag() -> None:
    """Com imagem: usa o modelo de visão, anexa a imagem e não busca na web."""
    llm = FakeLLMProvider(tokens=["vejo um gato"])
    service = build_conversation_service(llm=llm)  # rag_enabled=True por padrão
    events = await _collect(service, "o que é isto?", images=["QkFTRTY0"])

    assert not any(isinstance(e, SourcesGathered) for e in events)  # sem RAG
    assert llm.models[-1] == "llava"  # modelo de visão default
    user = [m for m in llm.calls[-1] if m.role == "user"][-1]
    assert user.images == ("QkFTRTY0",)


async def test_run_without_image_keeps_text_model() -> None:
    """Sem imagem, o modelo continua o default (None => provedor decide)."""
    llm = FakeLLMProvider(tokens=["oi"])
    service = build_conversation_service(llm=llm, rag_enabled=False)
    await _collect(service, "olá")
    assert llm.models[-1] is None
    assert llm.calls[-1][-1].images == ()


async def test_screen_sensor_captures_png() -> None:
    """O sensor de tela devolve um Percept de imagem PNG (grabber injetado)."""
    sensor = ScreenCaptureSensor(grabber=lambda: b"\x89PNGfake")
    percept = await sensor.capture()
    assert percept.modality is Modality.SCREEN
    assert percept.mime == "image/png"
    assert percept.data == b"\x89PNGfake"


async def test_manager_snapshot_does_not_enqueue() -> None:
    """snapshot() captura sem publicar no fluxo de percepção."""
    registry = SensorRegistry()
    registry.register(SCREEN_DESCRIPTOR, lambda: ScreenCaptureSensor(grabber=lambda: b"png"))
    manager = SensorManager(registry)
    percept = await manager.snapshot("screen")
    assert percept.data == b"png"
    assert manager._queue.empty()  # nada foi enfileirado


def test_rest_capture_screen_returns_base64() -> None:
    """GET /api/vision/screen devolve a imagem em base64."""
    app = create_app()
    registry = SensorRegistry()
    registry.register(
        SCREEN_DESCRIPTOR, lambda: ScreenCaptureSensor(grabber=lambda: b"\x89PNGdata")
    )
    app.state.sensor_manager = SensorManager(registry)

    resp = TestClient(app).get("/api/vision/screen")
    assert resp.status_code == 200
    body = resp.json()
    assert base64.b64decode(body["image"]) == b"\x89PNGdata"
    assert body["mime"] == "image/png"
