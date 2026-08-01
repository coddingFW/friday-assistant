"""Rotas REST — usadas apenas para configuração, CRUD, histórico e perfis.

Comunicação em tempo real NÃO passa por aqui; ver ``backend.api.websocket``.
"""

from fastapi import APIRouter

from backend.api.rest import health, llm, sensors

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(llm.router, prefix="/llm", tags=["llm"])
router.include_router(sensors.router, tags=["sensors"])

__all__ = ["router"]
