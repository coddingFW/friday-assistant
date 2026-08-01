"""Fábrica de provedores de LLM — seleção da estratégia por configuração.

Concretiza o Strategy Pattern: dado o valor de ``settings.llm_provider``,
devolve o adapter correto já pronto. Adicionar um novo provedor no futuro é
registrar uma nova entrada aqui, sem tocar no domínio nem na camada de API.
"""

from __future__ import annotations

import httpx

from backend.brain.ports import LLMProvider
from backend.brain.providers.ollama_provider import OllamaProvider
from backend.config.settings import Settings
from backend.utils.errors import ProviderConfigError


def create_llm_provider(settings: Settings, client: httpx.AsyncClient) -> LLMProvider:
    """Cria o provedor de LLM correspondente à configuração ativa.

    Args:
        settings: Configuração da aplicação.
        client: Cliente HTTP compartilhado, já apontado para o serviço.

    Returns:
        Instância que satisfaz a porta :class:`LLMProvider`.

    Raises:
        ProviderConfigError: Se ``llm_provider`` não corresponder a nenhuma
            estratégia registrada.
    """
    provider = settings.llm_provider.strip().lower()

    if provider == "ollama":
        return OllamaProvider(client=client, default_model=settings.llm_model)

    raise ProviderConfigError(
        f"Provedor de LLM desconhecido: '{settings.llm_provider}'. "
        "Provedores suportados: ollama."
    )
