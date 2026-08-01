"""Rotas WebSocket — toda a comunicação em tempo real do sistema.

Streaming de respostas do LLM, indicadores de estado ("Pensando", "Respondendo"),
e (fases futuras) transcrição parcial e sincronização do avatar.
"""

from fastapi import APIRouter

from backend.api.websocket import chat

router = APIRouter()
router.include_router(chat.router)

__all__ = ["router"]
