"""Portas (interfaces) da camada de memória — Ports & Adapters.

O domínio depende apenas destas abstrações, nunca de um banco concreto. Qualquer
mecanismo de persistência (SQLite hoje; Postgres, arquivo etc. no futuro) é um
*adapter* que implementa :class:`ConversationRepository` — o Repository Pattern
exigido pela arquitetura (ADR-0012). A troca de backend vira configuração.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from backend.brain.ports import Role


@dataclass(frozen=True, slots=True)
class Conversation:
    """Metadados de uma conversa persistida (sem as mensagens)."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    #: Número de mensagens (user+assistant) na conversa. 0 quando não contado.
    message_count: int = 0


@dataclass(frozen=True, slots=True)
class StoredMessage:
    """Uma mensagem persistida de uma conversa, em ordem cronológica."""

    id: int
    conversation_id: str
    role: Role
    content: str
    model: str | None
    created_at: datetime


@runtime_checkable
class ConversationRepository(Protocol):
    """Contrato de persistência de conversas e mensagens.

    Implementações devem ser assíncronas (I/O fora do event loop) e traduzir
    falhas de infraestrutura para :class:`backend.utils.errors.StorageError`.
    """

    async def create_conversation(self, title: str) -> Conversation:
        """Cria uma conversa nova e a devolve com id/timestamps preenchidos."""
        ...

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Retorna a conversa pelo id, ou ``None`` se não existir."""
        ...

    async def list_conversations(self, *, limit: int = 50) -> list[Conversation]:
        """Lista conversas da mais recente para a mais antiga (por ``updated_at``)."""
        ...

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Apaga a conversa e suas mensagens. Retorna ``False`` se não existia."""
        ...

    async def add_message(
        self,
        conversation_id: str,
        role: Role,
        content: str,
        *,
        model: str | None = None,
    ) -> StoredMessage:
        """Anexa uma mensagem à conversa e atualiza seu ``updated_at``."""
        ...

    async def recent_messages(
        self, conversation_id: str, *, limit: int
    ) -> list[StoredMessage]:
        """Retorna as ``limit`` mensagens mais recentes, em ordem cronológica."""
        ...

    async def list_messages(self, conversation_id: str) -> list[StoredMessage]:
        """Retorna todas as mensagens da conversa, em ordem cronológica."""
        ...
