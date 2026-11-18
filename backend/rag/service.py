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

    def _identity(self, images: Sequence[str]) -> ChatMessage:
        """Identidade da Friday; a descrição da própria tela só vai com imagem.

        Sem imagem não há tela para reconhecer, então anexar a descrição só
        gastaria tokens (e tempo de leitura do prompt) em todo turno.
        """
        content = self._settings.identity_prompt
        if images:
            content = f"{content}\n{self._settings.interface_prompt}"
        return ChatMessage(role="system", content=content)

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
        # Identidade primeiro (autoconhecimento — reconhece a própria tela),
        # depois as instruções de comportamento/RAG.
        messages = [
            self._identity(images),
            ChatMessage(role="system", content=self._settings.rag_system_prompt),
        ]
        messages.extend(history)
        context = build_context(results)
        if context:
            messages.append(ChatMessage(role="system", content=context))
        messages.append(
            ChatMessage(role="user", content=query, images=tuple(images))
        )
        return messages

    def build_code_messages(
        self,
        query: str,
        history: Sequence[ChatMessage] = (),
        context_blocks: Sequence[str] = (),
        code_prompt: str | None = None,
        images: Sequence[str] = (),
    ) -> list[ChatMessage]:
        """Monta as mensagens de um turno de código (projeto local — Fase 10).

        Ordem: identidade + prompt de ensino (código) + um bloco de sistema por
        arquivo do projeto + histórico + a pergunta. Sem contexto de busca web (a
        pergunta é sobre o projeto local, não a web).

        Os arquivos vêm ANTES do histórico de propósito: o Ollama reaproveita o
        trecho inicial do prompt que não mudou desde o turno anterior (cache de
        prefixo). Arquivos costumam ser os mesmos entre perguntas seguidas e são a
        parte mais pesada; o histórico muda a cada turno. Nesta ordem, só o
        histórico novo e a pergunta precisam ser lidos de novo.
        """
        messages = [
            self._identity(images),
            ChatMessage(
                role="system",
                content=code_prompt or self._settings.code_system_prompt,
            ),
        ]
        for block in context_blocks:
            messages.append(ChatMessage(role="system", content=block))
        messages.extend(history)
        messages.append(
            ChatMessage(role="user", content=query, images=tuple(images))
        )
        return messages
