"""Endpoints REST de conversas (Fase 9) — memória de longo prazo.

Listar, ler e apagar conversas persistidas. O tempo real (enviar mensagem,
receber tokens) continua no WebSocket; aqui é só CRUD/histórico, conforme a
divisão REST × WebSocket do manifesto.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.api.dependencies import get_memory_service
from backend.memory.service import MemoryService


class ConversationSummary(BaseModel):
    """Metadados de uma conversa (sem as mensagens)."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class MessageOut(BaseModel):
    """Uma mensagem persistida de uma conversa."""

    role: str
    content: str
    model: str | None = None
    created_at: datetime


class ConversationDetail(ConversationSummary):
    """Uma conversa com todas as suas mensagens, em ordem cronológica."""

    messages: list[MessageOut]


router = APIRouter()


@router.get(
    "/conversations",
    response_model=list[ConversationSummary],
    summary="Lista as conversas",
)
async def list_conversations(
    memory: Annotated[MemoryService, Depends(get_memory_service)],
    limit: int = 50,
) -> list[ConversationSummary]:
    """Lista as conversas da mais recente para a mais antiga."""
    convs = await memory.list_conversations(limit=limit)
    return [
        ConversationSummary(
            id=c.id,
            title=c.title,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=c.message_count,
        )
        for c in convs
    ]


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Lê uma conversa com suas mensagens",
)
async def get_conversation(
    conversation_id: str,
    memory: Annotated[MemoryService, Depends(get_memory_service)],
) -> ConversationDetail:
    """Retorna a conversa e todas as suas mensagens."""
    conv = await memory.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada."
        )
    messages = await memory.list_messages(conversation_id)
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=conv.message_count,
        messages=[
            MessageOut(
                role=m.role,
                content=m.content,
                model=m.model,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Apaga uma conversa",
)
async def delete_conversation(
    conversation_id: str,
    memory: Annotated[MemoryService, Depends(get_memory_service)],
) -> None:
    """Apaga a conversa e suas mensagens. 404 se não existir."""
    deleted = await memory.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada."
        )
