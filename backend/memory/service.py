"""Serviço de memória de longo prazo — fachada de domínio sobre o repositório.

É o único ponto que a API (WebSocket e REST) conhece. Traduz entre o mundo do
domínio da conversa (:class:`~backend.brain.ports.ChatMessage`) e o mundo
persistido (:class:`~backend.memory.ports.StoredMessage`), deriva o título de uma
conversa nova a partir da primeira mensagem e grava um turno completo.

Regra de projeto: só texto é persistido no histórico. Imagens (visão) são de uso
único no turno e não voltam ao LLM depois — mantê-las fora do banco o deixa leve.
"""

from __future__ import annotations

from backend.brain.ports import ChatMessage
from backend.memory.ports import Conversation, ConversationRepository, StoredMessage

#: Tamanho máximo do título derivado da primeira mensagem do usuário.
_TITLE_MAX = 60


def _derive_title(first_message: str) -> str:
    """Deriva um título curto e legível a partir da primeira mensagem."""
    # Primeira linha não vazia, colapsando espaços; corta no limite com reticências.
    linha = next(
        (ln.strip() for ln in first_message.splitlines() if ln.strip()), ""
    )
    linha = " ".join(linha.split())
    if not linha:
        return "Nova conversa"
    if len(linha) > _TITLE_MAX:
        return linha[: _TITLE_MAX - 1].rstrip() + "…"
    return linha


class MemoryService:
    """Casos de uso de memória persistente, sobre a porta do repositório."""

    def __init__(self, repository: ConversationRepository) -> None:
        self._repo = repository

    # --- Conversas ----------------------------------------------------------

    async def start_conversation(self, first_message: str) -> Conversation:
        """Cria uma conversa nova, com título derivado da primeira mensagem."""
        return await self._repo.create_conversation(_derive_title(first_message))

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Retorna a conversa pelo id, ou ``None`` se não existir."""
        return await self._repo.get_conversation(conversation_id)

    async def list_conversations(self, *, limit: int = 50) -> list[Conversation]:
        """Lista conversas da mais recente para a mais antiga."""
        return await self._repo.list_conversations(limit=limit)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Apaga a conversa e suas mensagens."""
        return await self._repo.delete_conversation(conversation_id)

    async def list_messages(self, conversation_id: str) -> list[StoredMessage]:
        """Todas as mensagens de uma conversa, em ordem cronológica."""
        return await self._repo.list_messages(conversation_id)

    # --- Integração com o turno de conversa --------------------------------

    async def history_window(
        self, conversation_id: str, *, limit: int
    ) -> list[ChatMessage]:
        """Janela recente da conversa como ``ChatMessage`` (contexto do LLM).

        Devolve as ``limit`` mensagens mais recentes em ordem cronológica, prontas
        para semear o histórico multi-turno. Só texto (sem imagens, por decisão).
        """
        stored = await self._repo.recent_messages(conversation_id, limit=limit)
        return [ChatMessage(role=m.role, content=m.content) for m in stored]

    async def record_turn(
        self,
        conversation_id: str,
        user_text: str,
        answer: str,
        *,
        model: str | None = None,
    ) -> None:
        """Persiste o par (usuário, assistente) de um turno bem-sucedido."""
        await self._repo.add_message(conversation_id, "user", user_text, model=model)
        await self._repo.add_message(
            conversation_id, "assistant", answer, model=model
        )
