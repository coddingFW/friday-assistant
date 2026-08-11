"""Endpoints REST de visão (Fase 8) — captura de tela do Host.

A captura acontece no Host (via o ``ScreenCaptureSensor``) e o cliente recebe a
imagem em base64 para anexar a uma mensagem destinada ao LLM de visão.
"""

from __future__ import annotations

import base64
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.api.dependencies import get_sensor_manager
from backend.config.settings import Settings, get_settings
from backend.perception.manager import SensorManager
from backend.perception.sensors.screen import SCREEN_DESCRIPTOR
from backend.utils.errors import SensorError, SensorNotFoundError


class CaptureResponse(BaseModel):
    """Imagem capturada, pronta para anexar a uma mensagem."""

    image: str  # base64 (sem prefixo data:)
    mime: str


router = APIRouter()


@router.get("/vision/screen", response_model=CaptureResponse, summary="Captura a tela")
async def capture_screen(
    manager: Annotated[SensorManager, Depends(get_sensor_manager)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CaptureResponse:
    """Tira um screenshot do Host e devolve a imagem em base64."""
    if not settings.vision_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Visão desativada."
        )
    try:
        percept = await manager.snapshot(SCREEN_DESCRIPTOR.id)
    except SensorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except SensorError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    data = percept.data if isinstance(percept.data, bytes) else b""
    return CaptureResponse(image=base64.b64encode(data).decode("ascii"), mime=percept.mime or "image/png")
