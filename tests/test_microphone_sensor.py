"""Testes do endpointer por energia e do stream do MicrophoneSensor (sem áudio real)."""

from __future__ import annotations

import asyncio

import numpy as np

from backend.perception.modality import Modality
from backend.perception.sensors.microphone import EnergyEndpointer, MicrophoneSensor

_FRAME = 480  # 30 ms @ 16 kHz


def _loud() -> bytes:
    return (np.ones(_FRAME, dtype=np.int16) * 8000).tobytes()


def _silent() -> bytes:
    return np.zeros(_FRAME, dtype=np.int16).tobytes()


def _endpointer(**overrides: object) -> EnergyEndpointer:
    opts = dict(
        frame_ms=30,
        silence_ms=90,          # 3 frames de silêncio encerram
        energy_threshold=500.0,
        min_speech_ms=60,       # exige >= 2 frames de fala
        max_utterance_ms=3000,
    )
    opts.update(overrides)
    return EnergyEndpointer(**opts)  # type: ignore[arg-type]


def test_ignores_pure_silence() -> None:
    ep = _endpointer()
    for _ in range(10):
        assert ep.push(_silent()) is None


def test_emits_utterance_after_speech_then_silence() -> None:
    ep = _endpointer()
    assert ep.push(_loud()) is None
    assert ep.push(_loud()) is None       # 60 ms de fala
    assert ep.push(_silent()) is None     # 30 ms silêncio
    assert ep.push(_silent()) is None     # 60 ms
    utterance = ep.push(_silent())        # 90 ms -> endpoint
    assert utterance is not None
    assert len(utterance) == 5 * _FRAME * 2  # 2 fala + 3 silêncio, int16


def test_discards_speech_shorter_than_minimum() -> None:
    ep = _endpointer(min_speech_ms=120)   # exige 4 frames de fala
    assert ep.push(_loud()) is None       # 30 ms de fala apenas
    assert ep.push(_silent()) is None
    assert ep.push(_silent()) is None
    assert ep.push(_silent()) is None     # endpoint, mas fala < mínimo -> None


def test_flushes_at_max_length() -> None:
    ep = _endpointer(max_utterance_ms=90)  # corta em 3 frames
    assert ep.push(_loud()) is None
    assert ep.push(_loud()) is None
    utterance = ep.push(_loud())           # 90 ms -> limite máximo
    assert utterance is not None
    assert len(utterance) == 3 * _FRAME * 2


def test_manual_flush_returns_pending_speech() -> None:
    ep = _endpointer()
    ep.push(_loud())
    ep.push(_loud())                       # fala em curso, sem endpoint
    utterance = ep.flush()
    assert utterance is not None
    assert len(utterance) == 2 * _FRAME * 2


async def test_stream_yields_percept_from_queue() -> None:
    """stream() consome a fila interna e emite um Percept de áudio por fala."""
    sensor = MicrophoneSensor(
        sample_rate=16000,
        frame_ms=30,
        silence_ms=90,
        energy_threshold=500.0,
        min_speech_ms=60,
        max_utterance_ms=3000,
    )
    sensor._queue = asyncio.Queue()  # injeta a fila sem abrir dispositivo
    for _ in range(2):
        sensor._queue.put_nowait(_loud())
    for _ in range(3):
        sensor._queue.put_nowait(_silent())

    gen = sensor.stream()
    try:
        percept = await asyncio.wait_for(gen.__anext__(), timeout=1.0)
    finally:
        await gen.aclose()

    assert percept.modality is Modality.AUDIO
    assert percept.source_id == "microphone"
    assert percept.metadata["sample_rate"] == 16000
    assert isinstance(percept.data, bytes) and len(percept.data) == 5 * _FRAME * 2
