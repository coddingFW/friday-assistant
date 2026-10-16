"""Testes da Fase 8 (visão): imagem no turno, sensor de tela e endpoint REST."""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from backend.brain.events import SourcesGathered
from backend.main import create_app
from backend.perception.manager import SensorManager
from backend.perception.modality import Modality
from backend.perception.registry import SensorRegistry
from backend.perception.sensors.ocr import OCR_DESCRIPTOR, OcrSensor
from backend.perception.sensors.screen import SCREEN_DESCRIPTOR, ScreenCaptureSensor
from backend.utils.errors import OcrUnavailableError, SensorError
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


# --- OCR (Tesseract, OnDemand) ---------------------------------------------


async def test_ocr_sensor_extracts_text() -> None:
    """O sensor de OCR devolve um Percept OCR_TEXT com o texto (aparado)."""
    sensor = OcrSensor(engine=lambda data, lang: "  olá mundo\n")
    percept = await sensor.capture(image=b"\x89PNGfake")
    assert percept.modality is Modality.OCR_TEXT
    assert percept.mime == "text/plain"
    assert percept.data == "olá mundo"
    assert percept.metadata == {"lang": "por+eng", "chars": len("olá mundo")}


async def test_ocr_sensor_lang_override() -> None:
    """O idioma por captura sobrescreve o padrão do sensor."""
    seen: dict[str, str] = {}

    def engine(data: bytes, lang: str) -> str:
        seen["lang"] = lang
        return "text"

    sensor = OcrSensor(lang="por", engine=engine)
    percept = await sensor.capture(image=b"img", lang="eng")
    assert seen["lang"] == "eng"
    assert percept.metadata["lang"] == "eng"


async def test_ocr_sensor_requires_image() -> None:
    """Sem imagem (bytes vazios), o sensor recusa com SensorError."""
    sensor = OcrSensor(engine=lambda data, lang: "x")
    with pytest.raises(SensorError):
        await sensor.capture(image=b"")


def _ocr_app(engine) -> object:
    """App de teste com o sensor de OCR (motor injetado) no manager."""
    app = create_app()
    registry = SensorRegistry()
    registry.register(OCR_DESCRIPTOR, lambda: OcrSensor(engine=engine))
    app.state.sensor_manager = SensorManager(registry)
    return app


def test_rest_ocr_upload_returns_text() -> None:
    """POST /api/vision/ocr (upload) devolve o texto extraído da imagem."""
    app = _ocr_app(lambda data, lang: "texto lido")
    image = base64.b64encode(b"\x89PNGdata").decode("ascii")

    resp = TestClient(app).post("/api/vision/ocr", json={"image": image})
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "texto lido"
    assert body["chars"] == len("texto lido")
    assert body["lang"] == "por+eng"


def test_rest_ocr_screen_captures_then_ocrs() -> None:
    """POST /api/vision/ocr (source=screen) captura a tela e depois faz OCR."""
    app = create_app()
    registry = SensorRegistry()
    registry.register(
        SCREEN_DESCRIPTOR, lambda: ScreenCaptureSensor(grabber=lambda: b"PNGSHOT")
    )
    captured: dict[str, bytes] = {}

    def engine(data: bytes, lang: str) -> str:
        captured["data"] = data
        return "da tela"

    registry.register(OCR_DESCRIPTOR, lambda: OcrSensor(engine=engine))
    app.state.sensor_manager = SensorManager(registry)

    resp = TestClient(app).post("/api/vision/ocr", json={"source": "screen"})
    assert resp.status_code == 200
    assert resp.json()["text"] == "da tela"
    assert captured["data"] == b"PNGSHOT"  # o OCR recebeu os bytes do screenshot


def test_rest_ocr_upload_requires_image() -> None:
    """source=upload sem imagem devolve 400."""
    app = _ocr_app(lambda data, lang: "x")
    resp = TestClient(app).post("/api/vision/ocr", json={"source": "upload"})
    assert resp.status_code == 400


def test_rest_ocr_invalid_base64_returns_400() -> None:
    """Imagem base64 malformada devolve 400."""
    app = _ocr_app(lambda data, lang: "x")
    resp = TestClient(app).post("/api/vision/ocr", json={"image": "!!!nãobase64!!!"})
    assert resp.status_code == 400


def test_rest_ocr_unavailable_returns_503() -> None:
    """Sem o Tesseract, o motor levanta OcrUnavailableError → 503 com orientação."""

    def engine(data: bytes, lang: str) -> str:
        raise OcrUnavailableError("Tesseract não encontrado.")

    app = _ocr_app(engine)
    image = base64.b64encode(b"data").decode("ascii")
    resp = TestClient(app).post("/api/vision/ocr", json={"image": image})
    assert resp.status_code == 503
    assert "Tesseract" in resp.json()["detail"]
