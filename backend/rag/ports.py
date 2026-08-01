"""Portas da camada de RAG — abstração do provedor de busca (Strategy).

O domínio depende de :class:`SearchProvider`, nunca de uma biblioteca concreta.
Trocar DuckDuckGo por outra fonte é adicionar um adapter e ajustar a config.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Um resultado de busca normalizado."""

    title: str
    url: str
    snippet: str


@runtime_checkable
class SearchProvider(Protocol):
    """Contrato de um provedor de busca web."""

    name: str

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        """Retorna até ``max_results`` resultados para a consulta.

        Raises:
            SearchUnavailableError: Se a busca falhar ou o serviço estiver indisponível.
        """
        ...
