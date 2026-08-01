"""Adapter de busca via DuckDuckGo (biblioteca ``ddgs``).

A ``ddgs`` é síncrona; a chamada é despachada para uma thread para não bloquear
o event loop. A dependência é importada **dentro** do método, de modo que a mera
construção do provedor (no startup) não exija a biblioteca — degradação graciosa.
"""

from __future__ import annotations

import asyncio

from backend.rag.ports import SearchResult
from backend.utils.errors import SearchUnavailableError
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class DuckDuckGoSearchProvider:
    """Provedor de busca web baseado no DuckDuckGo."""

    name = "duckduckgo"

    def __init__(self, *, region: str = "wt-wt", timeout: float = 10.0) -> None:
        self._region = region
        self._timeout = timeout

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        """Executa a busca e normaliza os resultados em :class:`SearchResult`."""
        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(self._blocking_search, query, max_results),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError as exc:
            raise SearchUnavailableError("Busca web excedeu o tempo limite.") from exc
        except Exception as exc:  # noqa: BLE001 - isola qualquer falha da lib
            logger.warning("ddg_search_failed", error=str(exc))
            raise SearchUnavailableError(f"Falha na busca web: {exc}") from exc

        results = [
            SearchResult(
                title=item.get("title", "").strip(),
                url=item.get("href", "").strip(),
                snippet=item.get("body", "").strip(),
            )
            for item in raw
        ]
        logger.info("ddg_search_ok", query=query, results=len(results))
        return results

    def _blocking_search(self, query: str, max_results: int) -> list[dict[str, str]]:
        """Chamada síncrona à ``ddgs`` (executada em thread separada)."""
        from ddgs import DDGS

        with DDGS() as ddgs:
            return list(
                ddgs.text(query, region=self._region, max_results=max_results)
            )
