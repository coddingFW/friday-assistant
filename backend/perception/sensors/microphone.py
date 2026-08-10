"""Sensor de microfone — primeiro ``StreamingSensor`` concreto (Fase 6).

Captura o microfone padrão do Host via ``sounddevice`` (PortAudio) e segmenta o
fluxo contínuo em **falas** (utterances) usando um endpointer por energia (VAD
simples baseado em RMS, sem dependências nativas a compilar). Cada fala vira um
:class:`Percept` de áudio (PCM 16-bit mono) publicado na camada de percepção — o
Brain nunca toca no dispositivo.

O ``sounddevice`` é importado preguiçosamente em :meth:`open`, para o módulo
poder ser importado (e o endpointer testado) em ambientes sem áudio/PortAudio.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from backend.perception.modality import Modality, Percept
from backend.perception.ports import SensorDescriptor, SensorKind
from backend.utils.errors import AudioCaptureError
from backend.utils.logging import get_logger

logger = get_logger(__name__)

MICROPHONE_DESCRIPTOR = SensorDescriptor(
    id="microphone",
    modality=Modality.AUDIO,
    kind=SensorKind.STREAMING,
    name="Microfone",
    description=(
        "Captura o microfone padrão do Host e emite falas (utterances) como "
        "percepções de áudio PCM 16-bit mono."
    ),
)


def _rms_int16(frame: bytes) -> float:
    """RMS de um bloco PCM int16 (escala 0..32767). 0 se vazio."""
    import numpy as np

    if not frame:
        return 0.0
    samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples * samples)))


class EnergyEndpointer:
    """Detecta o início/fim de uma fala por energia (VAD por RMS).

    Alimente frames PCM int16 (mesma duração) com :meth:`push`. Quando uma fala
    termina (silêncio prolongado após fala com duração mínima) ou atinge o limite
    máximo, devolve os bytes PCM da fala; caso contrário, ``None``. É lógica pura,
    sem áudio — testável de forma determinística.
    """

    def __init__(
        self,
        *,
        frame_ms: int,
        silence_ms: int,
        energy_threshold: float,
        min_speech_ms: int,
        max_utterance_ms: int,
    ) -> None:
        self._frame_ms = frame_ms
        self._silence_ms = silence_ms
        self._threshold = energy_threshold
        self._min_speech_ms = min_speech_ms
        self._max_utterance_ms = max_utterance_ms
        self._reset()

    def _reset(self) -> None:
        self._buf = bytearray()
        self._in_speech = False
        self._speech_ms = 0
        self._silence_run_ms = 0

    def push(self, frame: bytes) -> bytes | None:
        """Consome um frame; devolve a fala completa (PCM) ou ``None``."""
        is_speech = _rms_int16(frame) >= self._threshold
        if is_speech:
            self._in_speech = True
            self._speech_ms += self._frame_ms
            self._silence_run_ms = 0
            self._buf += frame
        elif self._in_speech:
            # Mantém o silêncio final dentro da fala (cauda natural).
            self._buf += frame
            self._silence_run_ms += self._frame_ms
            if self._silence_run_ms >= self._silence_ms:
                return self._flush()
        # Salvaguarda contra fala interminável.
        if self._in_speech and self._speech_ms >= self._max_utterance_ms:
            return self._flush()
        return None

    def flush(self) -> bytes | None:
        """Encerra manualmente (ex.: parar de ouvir); devolve fala pendente."""
        return self._flush()

    def _flush(self) -> bytes | None:
        utterance = bytes(self._buf)
        speech_ms = self._speech_ms
        self._reset()
        if speech_ms >= self._min_speech_ms and utterance:
            return utterance
        return None


class MicrophoneSensor:
    """``StreamingSensor`` que emite falas do microfone como percepções de áudio."""

    descriptor = MICROPHONE_DESCRIPTOR

    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        frame_ms: int = 30,
        silence_ms: int = 800,
        energy_threshold: float = 500.0,
        min_speech_ms: int = 300,
        max_utterance_ms: int = 15000,
        device: int | str | None = None,
    ) -> None:
        self._sample_rate = sample_rate
        self._frame_ms = frame_ms
        self._frame_samples = max(1, int(sample_rate * frame_ms / 1000))
        self._device = device
        self._endpointer_opts = dict(
            frame_ms=frame_ms,
            silence_ms=silence_ms,
            energy_threshold=energy_threshold,
            min_speech_ms=min_speech_ms,
            max_utterance_ms=max_utterance_ms,
        )
        self._queue: asyncio.Queue[bytes] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stream = None

    async def open(self) -> None:
        """Abre o stream de captura do microfone padrão do Host."""
        try:
            import sounddevice as sd
        except (ImportError, OSError) as exc:  # PortAudio ausente etc.
            raise AudioCaptureError(
                f"sounddevice/PortAudio indisponível: {exc}"
            ) from exc

        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        try:
            self._stream = sd.RawInputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self._frame_samples,
                device=self._device,
                callback=self._on_audio,
            )
            self._stream.start()
        except Exception as exc:  # noqa: BLE001 - traduz falha de dispositivo
            raise AudioCaptureError(f"Falha ao abrir o microfone: {exc}") from exc
        logger.info(
            "microphone_opened",
            sample_rate=self._sample_rate,
            frame_ms=self._frame_ms,
            device=str(self._device),
        )

    def _on_audio(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        """Callback do PortAudio (thread separada): enfileira o frame PCM."""
        if status:
            logger.warning("microphone_status", status=str(status))
        data = bytes(indata)
        loop, queue = self._loop, self._queue
        if loop is not None and queue is not None:
            loop.call_soon_threadsafe(queue.put_nowait, data)

    async def stream(self) -> AsyncIterator[Percept]:
        """Emite um :class:`Percept` de áudio por fala detectada, até cancelar."""
        if self._queue is None:
            raise AudioCaptureError("Microfone não aberto (chame open() antes).")
        endpointer = EnergyEndpointer(**self._endpointer_opts)
        while True:
            frame = await self._queue.get()
            utterance = endpointer.push(frame)
            if utterance:
                yield self._to_percept(utterance)

    def _to_percept(self, pcm: bytes) -> Percept:
        return Percept(
            modality=Modality.AUDIO,
            source_id=self.descriptor.id,
            data=pcm,
            mime="audio/pcm",
            metadata={
                "sample_rate": self._sample_rate,
                "channels": 1,
                "sample_width": 2,
            },
        )

    async def close(self) -> None:
        """Encerra o stream de captura e libera o dispositivo."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:  # noqa: BLE001 - encerramento tolerante
                logger.warning("microphone_close_error", error=str(exc))
            self._stream = None
        logger.info("microphone_closed")
