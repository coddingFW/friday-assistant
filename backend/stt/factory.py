"""Fábrica do provedor de STT — seleção da estratégia por configuração."""

from __future__ import annotations

from backend.config.settings import Settings
from backend.stt.ports import STTProvider
from backend.stt.providers.whisper import WhisperSTTProvider
from backend.utils.errors import ProviderConfigError


def create_stt_provider(settings: Settings) -> STTProvider:
    """Cria o provedor de STT conforme ``settings.stt_provider``.

    Raises:
        ProviderConfigError: Se o provedor configurado for desconhecido.
    """
    provider = settings.stt_provider.strip().lower()
    if provider == "whisper":
        return WhisperSTTProvider(
            model=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            language=settings.whisper_language or None,
            beam_size=settings.whisper_beam_size,
        )
    raise ProviderConfigError(
        f"Provedor de STT desconhecido: '{settings.stt_provider}'. "
        "Provedores suportados: whisper."
    )
