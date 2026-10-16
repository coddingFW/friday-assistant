"""Endpoints REST de visão (Fase 8) — captura de tela do Host.

A captura acontece no Host (via o ``ScreenCaptureSensor``) e o cliente recebe a
imagem em base64 para anexar a uma mensagem destinada ao LLM de visão.
"""

from __future__ import annotations

import base64
import binascii
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.api.dependencies import get_sensor_manager
from backend.config.settings import Settings, get_settings
from backend.perception.manager import SensorManager
from backend.perception.sensors.ocr import OCR_DESCRIPTOR
from backend.perception.sensors.screen import SCREEN_DESCRIPTOR
from backend.utils.errors import OcrUnavailableError, SensorError, SensorNotFoundError


class CaptureResponse(BaseModel):
    """Imagem capturada, pronta para anexar a uma mensagem."""

    image: str  # base64 (sem prefixo data:)
    mime: str


class OcrRequest(BaseModel):
    """Pedido de OCR: uma imagem enviada (base64) ou a tela do Host."""

    source: Literal["upload", "screen"] = "upload"
    image: str | None = None  # base64 (sem prefixo data:); exigido se source=upload
    lang: str | None = None  # sobrescreve o idioma do Tesseract (ex.: "eng")


class OcrResponse(BaseModel):
    """Texto extraído de uma imagem pelo OCR."""

    text: str
    lang: str
    chars: int


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


@router.post("/vision/ocr", response_model=OcrResponse, summary="OCR de uma imagem")
async def ocr_image(
    payload: OcrRequest,
    manager: Annotated[SensorManager, Depends(get_sensor_manager)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OcrResponse:
    """Extrai o texto literal de uma imagem enviada (base64) ou da tela do Host."""
    if not settings.vision_enabled or not settings.ocr_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OCR desativado."
        )

    # Fonte da imagem: a tela do Host (capturada agora) ou o upload do cliente.
    if payload.source == "screen":
        try:
            shot = await manager.snapshot(SCREEN_DESCRIPTOR.id)
        except SensorNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
            ) from exc
        except SensorError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc
        image = shot.data if isinstance(shot.data, bytes) else b""
    else:
        if not payload.image:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Envie a imagem em base64 (campo 'image').",
            )
        try:
            image = base64.b64decode(payload.image, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Imagem base64 inválida.",
            ) from exc

    try:
        percept = await manager.snapshot(OCR_DESCRIPTOR.id, image=image, lang=payload.lang)
    except SensorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except OcrUnavailableError as exc:
        # Pré-requisito ausente (Tesseract): 503 com orientação de instalação.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except SensorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    text = percept.data if isinstance(percept.data, str) else ""
    meta = percept.metadata
    return OcrResponse(text=text, lang=str(meta.get("lang", "")), chars=int(meta.get("chars", len(text))))
