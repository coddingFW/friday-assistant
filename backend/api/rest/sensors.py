"""Endpoints REST de descoberta de sensores (percepção multimodal).

Somente leitura na Fase 1: expõe o catálogo de sensores registrados (vazio
enquanto nenhum sensor concreto existir). A ativação/captura entra nas fases
que implementarem sensores reais, sempre por esta camada — nunca pelo Brain.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.dependencies import get_sensor_manager
from backend.perception.manager import SensorManager


class SensorInfo(BaseModel):
    """Descrição serializável de um sensor registrado."""

    id: str
    modality: str
    kind: str
    name: str
    description: str


class SensorsResponse(BaseModel):
    """Catálogo de sensores disponíveis no Host."""

    sensors: list[SensorInfo]


router = APIRouter()


@router.get("/sensors", response_model=SensorsResponse, summary="Sensores disponíveis")
async def list_sensors(
    manager: Annotated[SensorManager, Depends(get_sensor_manager)],
) -> SensorsResponse:
    """Lista os sensores registrados na camada de percepção."""
    return SensorsResponse(
        sensors=[
            SensorInfo(
                id=d.id,
                modality=d.modality.value,
                kind=d.kind.value,
                name=d.name,
                description=d.description,
            )
            for d in manager.available()
        ]
    )
