"""Testes do fluxo de escuta por voz (STT) no WebSocket de chat."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.perception.manager import SensorManager
from backend.perception.modality import Modality, Percept
from backend.perception.ports import SensorDescriptor, SensorKind
from backend.perception.registry import SensorRegistry
from backend.stt.ports import Transcript
from tests.conftest import build_conversation_service


class FakeMicSensor:
    """StreamingSensor falso: emite uma fala de áudio e depois bloqueia."""

    descriptor = SensorDescriptor(
        id="microphone",
        modality=Modality.AUDIO,
        kind=SensorKind.STREAMING,
        name="fake-mic",
        description="",
    )

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def stream(self):
        yield Percept(
            modality=Modality.AUDIO,
            source_id="microphone",
            data=b"\x01\x02" * 200,
            mime="audio/pcm",
            metadata={"sample_rate": 16000},
        )
        await asyncio.Event().wait()  # nenhuma outra fala


class FakeSTTProvider:
    """Provedor de STT falso: devolve sempre o mesmo texto."""

    name = "fake"

    def __init__(self, text: str) -> None:
        self._text = text
        self.calls: list[tuple[bytes, int]] = []

    async def health(self) -> bool:
        return True

    async def transcribe(self, pcm16: bytes, *, sample_rate: int = 16000) -> Transcript:
        self.calls.append((pcm16, sample_rate))
        return Transcript(text=self._text)


def _app_with_voice(text: str = "olá friday"):
    app = create_app()
    app.state.conversation_service = build_conversation_service()
    registry = SensorRegistry()
    registry.register(FakeMicSensor.descriptor, lambda: FakeMicSensor())
    app.state.sensor_manager = SensorManager(registry)
    app.state.stt_provider = FakeSTTProvider(text)
    return app


def test_ws_listen_emits_transcript() -> None:
    """listen_start -> status listening -> transcript -> listen_stop -> idle."""
    app = _app_with_voice("olá friday")
    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "listen_start"})
        assert ws.receive_json() == {"type": "status", "state": "listening"}
        assert ws.receive_json() == {
            "type": "transcript",
            "text": "olá friday",
            "final": True,
        }
        ws.send_json({"type": "listen_stop"})
        assert ws.receive_json() == {"type": "status", "state": "idle"}


def test_ws_listen_disabled_returns_error() -> None:
    """Sem STT/sensor, listen_start responde erro sem derrubar a conexão."""
    app = create_app()
    app.state.conversation_service = build_conversation_service()
    app.state.sensor_manager = None
    app.state.stt_provider = None
    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "listen_start"})
        assert ws.receive_json()["type"] == "error"
