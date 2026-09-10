"""Rotas REST — usadas apenas para configuração, CRUD, histórico e perfis.

Comunicação em tempo real NÃO passa por aqui; ver ``backend.api.websocket``.
"""

from fastapi import APIRouter

from backend.api.rest import (
    conversations,
    health,
    llm,
    sensors,
    vision,
    workspace,
)

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(llm.router, prefix="/llm", tags=["llm"])
router.include_router(sensors.router, tags=["sensors"])
router.include_router(vision.router, tags=["vision"])
router.include_router(conversations.router, tags=["conversations"])
router.include_router(workspace.router, tags=["workspace"])

__all__ = ["router"]
