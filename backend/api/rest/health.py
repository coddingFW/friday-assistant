"""Endpoints de saúde/liveness do backend e dos serviços locais."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.dependencies import get_llm_provider
from backend.brain.ports import LLMProvider
from backend.config.settings import Settings, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Estado geral do backend e das dependências externas."""

    status: str
    app: str
    version: str
    llm_provider: str
    llm_model: str
    llm_reachable: bool


@router.get("/health", response_model=HealthResponse, summary="Saúde do sistema")
async def health(
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> HealthResponse:
    """Retorna o estado do backend e se o provedor de LLM está acessível.

    O backend permanece ``ok`` mesmo com o LLM indisponível (degradação
    graciosa); ``llm_reachable`` indica o estado do serviço local.
    """
    from backend import __version__

    reachable = await provider.health()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=__version__,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        llm_reachable=reachable,
    )
