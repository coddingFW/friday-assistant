"""Testes da configuração central."""

from __future__ import annotations

import pytest

from backend.config.settings import Settings


def test_defaults() -> None:
    """Os defaults aprovados na arquitetura devem estar presentes."""
    settings = Settings(_env_file=None)
    assert settings.app_name == "Friday"
    assert settings.llm_provider == "ollama"
    assert settings.llm_model == "llama3.1:8b"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Trocar o modelo deve ser possível apenas por variável de ambiente."""
    monkeypatch.setenv("FRIDAY_LLM_MODEL", "qwen3")
    monkeypatch.setenv("FRIDAY_PORT", "9001")
    settings = Settings(_env_file=None)
    assert settings.llm_model == "qwen3"
    assert settings.port == 9001


def test_invalid_port_rejected() -> None:
    """Porta fora do intervalo válido deve falhar na validação."""
    with pytest.raises(ValueError):
        Settings(_env_file=None, port=70000)
