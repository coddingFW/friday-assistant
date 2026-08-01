"""Fábrica do provedor de busca — seleção da estratégia por configuração."""

from __future__ import annotations

from backend.config.settings import Settings
from backend.rag.ports import SearchProvider
from backend.rag.providers.duckduckgo import DuckDuckGoSearchProvider
from backend.utils.errors import ProviderConfigError


def create_search_provider(settings: Settings) -> SearchProvider:
    """Cria o provedor de busca conforme ``settings.rag_provider``.

    Raises:
        ProviderConfigError: Se o provedor configurado for desconhecido.
    """
    provider = settings.rag_provider.strip().lower()
    if provider == "duckduckgo":
        return DuckDuckGoSearchProvider(
            region=settings.rag_region, timeout=settings.rag_timeout
        )
    raise ProviderConfigError(
        f"Provedor de busca desconhecido: '{settings.rag_provider}'. "
        "Provedores suportados: duckduckgo."
    )
