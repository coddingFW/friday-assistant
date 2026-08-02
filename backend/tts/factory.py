"""Fábrica do provedor de TTS — seleção da estratégia por configuração."""

from __future__ import annotations

from backend.config.settings import Settings
from backend.tts.ports import TTSProvider
from backend.tts.providers.piper import PiperTTSProvider
from backend.utils.errors import ProviderConfigError


def create_tts_provider(settings: Settings) -> TTSProvider:
    """Cria o provedor de TTS conforme ``settings.tts_provider``.

    Raises:
        ProviderConfigError: Se o provedor configurado for desconhecido.
    """
    provider = settings.tts_provider.strip().lower()
    if provider == "piper":
        return PiperTTSProvider(
            binary=settings.piper_binary,
            voice=settings.piper_voice,
            timeout=settings.tts_timeout,
        )
    raise ProviderConfigError(
        f"Provedor de TTS desconhecido: '{settings.tts_provider}'. "
        "Provedores suportados: piper."
    )
