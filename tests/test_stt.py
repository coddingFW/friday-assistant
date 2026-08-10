"""Testes da camada de STT (fábrica e provedor Whisper — caminhos offline)."""

from __future__ import annotations

import numpy as np
import pytest

from backend.config.settings import Settings
from backend.stt.factory import create_stt_provider
from backend.stt.providers.whisper import WhisperSTTProvider, _resample_linear
from backend.utils.errors import ProviderConfigError


def test_factory_creates_whisper() -> None:
    """A fábrica devolve o adapter Whisper por padrão."""
    provider = create_stt_provider(Settings(_env_file=None))
    assert isinstance(provider, WhisperSTTProvider)


def test_factory_rejects_unknown_provider() -> None:
    """Provedor de STT desconhecido deve falhar na fábrica."""
    with pytest.raises(ProviderConfigError):
        create_stt_provider(Settings(_env_file=None, stt_provider="vosk"))


async def test_transcribe_empty_returns_empty_without_loading_model() -> None:
    """Áudio vazio devolve texto vazio sem carregar o modelo (rápido/offline)."""
    provider = WhisperSTTProvider(model="tiny")
    transcript = await provider.transcribe(b"")
    assert transcript.text == ""
    assert provider._model is None  # não tocou no motor pesado


def test_resample_linear_changes_length() -> None:
    """Reamostragem ajusta o número de amostras conforme a taxa destino."""
    src = np.linspace(-1, 1, num=16000, dtype=np.float32)  # 1 s @ 16 kHz
    out = _resample_linear(src, 16000, 8000)
    assert out.shape[0] == 8000
    same = _resample_linear(src, 16000, 16000)
    assert same.shape[0] == 16000
