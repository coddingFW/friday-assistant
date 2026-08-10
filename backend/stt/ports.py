"""Portas (interfaces) da camada de STT — Ports & Adapters.

O domínio depende apenas desta abstração, nunca de um motor concreto. Qualquer
provedor (Whisper via faster-whisper hoje; vosk, whisper.cpp etc. no futuro) é um
*adapter* que implementa :class:`STTProvider`, concretizando o Strategy Pattern:
trocar de motor de transcrição é uma decisão de configuração.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Transcript:
    """Resultado de uma transcrição.

    Attributes:
        text: Texto reconhecido (já sem espaços nas pontas).
        language: Idioma detectado/assumido (ex.: ``"pt"``), se disponível.
        duration: Duração do áudio em segundos, se disponível.
    """

    text: str
    language: str | None = None
    duration: float | None = None


@runtime_checkable
class STTProvider(Protocol):
    """Contrato que todo provedor de transcrição de voz deve cumprir.

    Implementações devem ser assíncronas, não bloquear o event loop (offload de
    trabalho pesado para thread) e traduzir falhas para :mod:`backend.utils.errors`.
    """

    #: Identificador curto do provedor (ex.: ``"whisper"``).
    name: str

    async def health(self) -> bool:
        """Retorna True se o provedor está pronto para transcrever."""
        ...

    async def transcribe(self, pcm16: bytes, *, sample_rate: int = 16000) -> Transcript:
        """Transcreve áudio PCM 16-bit mono.

        Args:
            pcm16: Amostras PCM assinadas de 16 bits (little-endian), 1 canal.
            sample_rate: Taxa de amostragem do ``pcm16`` (Hz).

        Returns:
            O :class:`Transcript` reconhecido (``text`` vazio se nada foi dito).

        Raises:
            STTUnavailableError: Motor indisponível/mal configurado.
            STTError: Demais falhas de transcrição.
        """
        ...
