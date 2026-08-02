"""Camada de síntese de voz (TTS).

Converte texto em áudio via um provedor local (Piper), atrás de uma porta —
o domínio não conhece a tecnologia concreta (Strategy Pattern, ADR-0003).
Por decisão de arquitetura (ADR-0007), o Host sintetiza e o cliente reproduz:
o áudio trafega ao cliente via WebSocket, nunca tocado no Host.
"""

from backend.tts.factory import create_tts_provider
from backend.tts.ports import SpeechAudio, TTSProvider

__all__ = ["create_tts_provider", "TTSProvider", "SpeechAudio"]
