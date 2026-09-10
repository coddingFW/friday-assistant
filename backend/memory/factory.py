"""Fábrica do repositório de memória — seleção da estratégia por configuração."""

from __future__ import annotations

from backend.config.settings import Settings
from backend.memory.ports import ConversationRepository
from backend.memory.providers.sqlite import SqliteConversationRepository


def create_conversation_repository(settings: Settings) -> ConversationRepository:
    """Cria o repositório de conversas conforme a configuração.

    Hoje há um único backend (SQLite); a fábrica existe para que adicionar outro
    no futuro seja uma decisão de configuração, sem tocar no domínio (ADR-0012).
    """
    return SqliteConversationRepository(settings.db_path)
