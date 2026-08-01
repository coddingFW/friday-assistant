"""Utilitários transversais: logging estruturado e hierarquia de erros."""

from backend.utils.errors import (
    FridayError,
    LLMError,
    LLMTimeoutError,
    LLMUnavailableError,
    ProviderConfigError,
    RagError,
    SearchUnavailableError,
    SensorError,
    SensorNotFoundError,
)
from backend.utils.logging import configure_logging, get_logger

__all__ = [
    "configure_logging",
    "get_logger",
    "FridayError",
    "LLMError",
    "LLMTimeoutError",
    "LLMUnavailableError",
    "ProviderConfigError",
    "RagError",
    "SearchUnavailableError",
    "SensorError",
    "SensorNotFoundError",
]
