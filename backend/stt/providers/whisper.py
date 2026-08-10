"""Adapter do Whisper (via faster-whisper / CTranslate2) para a porta STTProvider.

Transcreve localmente, sem rede após o primeiro download do modelo. A síntese é
pesada em CPU, então a inferência roda em um *worker thread* (:func:`asyncio.to_thread`),
mantendo o event loop livre — mesma lição do TTS (Piper). O modelo é carregado
preguiçosamente na primeira transcrição, para não pesar o startup nem exigir o
download em ambientes de teste.
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.stt.ports import Transcript
from backend.utils.errors import STTError, STTUnavailableError
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class WhisperSTTProvider:
    """Provedor de STT que delega a transcrição ao Whisper local (faster-whisper)."""

    name = "whisper"

    def __init__(
        self,
        *,
        model: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str | None = "pt",
        beam_size: int = 1,
        download_root: str | None = None,
    ) -> None:
        self._model_name = model
        self._device = device
        self._compute_type = compute_type
        self._language = language or None
        self._beam_size = beam_size
        self._download_root = download_root or None
        self._model: Any | None = None

    def _ensure_model(self) -> Any:
        """Carrega o modelo Whisper sob demanda (bloqueante; chamar em thread)."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:  # pragma: no cover - ambiente sem a lib
                raise STTUnavailableError(
                    "faster-whisper não está instalado (pip install faster-whisper)."
                ) from exc
            try:
                self._model = WhisperModel(
                    self._model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                    download_root=self._download_root,
                )
            except Exception as exc:  # noqa: BLE001 - traduz falha de carga do motor
                raise STTUnavailableError(
                    f"Falha ao carregar o modelo Whisper '{self._model_name}': {exc}"
                ) from exc
            logger.info(
                "whisper_model_loaded",
                model=self._model_name,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._model

    async def health(self) -> bool:
        """Retorna True se a biblioteca faster-whisper está importável."""
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return False
        return True

    async def transcribe(self, pcm16: bytes, *, sample_rate: int = 16000) -> Transcript:
        """Transcreve PCM 16-bit mono em texto (no worker thread)."""
        if not pcm16:
            return Transcript(text="")
        return await asyncio.to_thread(self._transcribe_blocking, pcm16, sample_rate)

    def _transcribe_blocking(self, pcm16: bytes, sample_rate: int) -> Transcript:
        """Conversão + inferência síncronas — executadas fora do event loop."""
        import numpy as np

        model = self._ensure_model()
        # PCM int16 -> float32 normalizado em [-1, 1], que é o que o Whisper espera.
        samples = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
        if sample_rate != 16000:
            samples = _resample_linear(samples, sample_rate, 16000)
        try:
            segments, info = model.transcribe(
                samples,
                language=self._language,
                beam_size=self._beam_size,
                vad_filter=True,
            )
            text = "".join(segment.text for segment in segments).strip()
        except Exception as exc:  # noqa: BLE001 - traduz falha de inferência
            raise STTError(f"Falha na transcrição do Whisper: {exc}") from exc
        logger.info("whisper_transcribed", chars=len(text), language=info.language)
        return Transcript(text=text, language=info.language, duration=info.duration)


def _resample_linear(samples: Any, src_rate: int, dst_rate: int) -> Any:
    """Reamostragem linear simples (suficiente para fala mono; evita libs extras)."""
    import numpy as np

    if src_rate == dst_rate or samples.size == 0:
        return samples
    duration = samples.size / float(src_rate)
    dst_len = int(round(duration * dst_rate))
    if dst_len <= 0:
        return samples[:0]
    src_idx = np.linspace(0, samples.size - 1, num=dst_len)
    return np.interp(src_idx, np.arange(samples.size), samples).astype(np.float32)
