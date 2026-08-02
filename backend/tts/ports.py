"""Portas da camada de TTS — abstração do provedor de síntese de voz.

O domínio depende de :class:`TTSProvider`, nunca de Piper/pyttsx3 diretamente.
Trocar o provedor é adicionar um adapter e ajustar a configuração (Strategy).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class SpeechAudio:
    """Áudio sintetizado, agnóstico de reprodução.

    Attributes:
        data: Bytes do áudio (WAV por padrão).
        mime: Tipo MIME (ex.: ``"audio/wav"``).
    """

    data: bytes
    mime: str = "audio/wav"


@runtime_checkable
class TTSProvider(Protocol):
    """Contrato de um provedor de síntese de voz."""

    name: str

    async def health(self) -> bool:
        """Retorna True se o provedor está pronto (binário + voz disponíveis)."""
        ...

    async def synthesize(self, text: str) -> SpeechAudio:
        """Sintetiza ``text`` em áudio.

        Raises:
            TTSUnavailableError: Provedor inacessível/mal configurado.
            TTSError: Demais falhas de síntese.
        """
        ...
