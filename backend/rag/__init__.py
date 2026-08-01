"""Camada de RAG (Retrieval-Augmented Generation).

Recupera resultados de busca web (top-N), constrói um contexto textual e o
disponibiliza para o LLM. O provedor de busca é uma estratégia plugável atrás de
uma porta — o domínio não conhece a biblioteca concreta (DuckDuckGo hoje).
"""

from backend.rag.factory import create_search_provider
from backend.rag.ports import SearchProvider, SearchResult
from backend.rag.service import RagService

__all__ = ["create_search_provider", "SearchProvider", "SearchResult", "RagService"]
