"""Endpoints REST informativos sobre o LLM (config e modelos disponíveis).

Apenas leitura/configuração — a geração de texto em si ocorre por WebSocket.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.api.dependencies import get_llm_provider
from backend.brain.ports import LLMProvider
from backend.config.settings import Settings, get_settings
from backend.utils.errors import LLMError, LLMUnavailableError


class LLMConfigResponse(BaseModel):
    """Configuração ativa do LLM."""

    provider: str
    model: str


class ModelsResponse(BaseModel):
    """Modelos disponíveis no provedor ativo."""

    provider: str
    models: list[str]


router = APIRouter()


@router.get("/config", response_model=LLMConfigResponse, summary="Config do LLM")
async def get_config(
    settings: Annotated[Settings, Depends(get_settings)],
) -> LLMConfigResponse:
    """Retorna o provedor e o modelo default atualmente configurados."""
    return LLMConfigResponse(provider=settings.llm_provider, model=settings.llm_model)


@router.get("/models", response_model=ModelsResponse, summary="Modelos disponíveis")
async def list_models(
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> ModelsResponse:
    """Lista os modelos instalados no provedor ativo.

    Raises:
        HTTPException: 503 se o serviço de LLM estiver indisponível.
    """
    try:
        models = await provider.list_models()
    except LLMUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return ModelsResponse(provider=settings.llm_provider, models=models)
