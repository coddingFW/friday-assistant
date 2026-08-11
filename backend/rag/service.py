"""Serviço de RAG — orquestra busca e montagem das mensagens para o LLM."""

from __future__ import annotations

from collections.abc import Sequence

from backend.brain.ports import ChatMessage
from backend.config.settings import Settings
from backend.rag.context import build_context
from backend.rag.ports import SearchProvider, SearchResult


class RagService:
    """Recupera contexto web e monta o histórico de mensagens do turno."""

    def __init__(self, search_provider: SearchProvider, settings: Settings) -> None:
        self._search = search_provider
        self._settings = settings

    async def retrieve(self, query: str) -> list[SearchResult]:
        """Recupera os top-N resultados de busca para a consulta."""
        return await self._search.search(query, self._settings.rag_max_results)

    def build_messages(
        self,
        query: str,
        results: list[SearchResult],
        history: Sequence[ChatMessage] = (),
        images: Sequence[str] = (),
    ) -> list[ChatMessage]:
        """Monta as mensagens: sistema + histórico + contexto (se houver) + usuário.

        Args:
            query: Pergunta do usuário.
            results: Resultados de busca já recuperados (pode ser vazio).
            history: Turnos anteriores (user/assistant) em ordem cronológica, para
                dar contexto multi-turno ao LLM. Vazio = conversa sem memória.
            images: Imagens (base64) anexadas à pergunta, para o LLM de visão.

        Returns:
            Lista de :class:`ChatMessage` pronta para o provedor de LLM.
        """
        messages = [
            ChatMessage(role="system", content=self._settings.rag_system_prompt)
        ]
        messages.extend(history)
        context = build_context(results)
        if context:
            messages.append(ChatMessage(role="system", content=context))
        messages.append(
            ChatMessage(role="user", content=query, images=tuple(images))
        )
        return messages
