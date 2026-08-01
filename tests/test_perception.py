"""Testes da camada de sensores (abstração multimodal).

Provam que um novo sensor pluga na arquitetura via registro/gerenciador **sem
modificar o núcleo**, exercitando streaming, captura on-demand e injeção externa.
Usam sensores falsos em memória — nenhum dispositivo ou visão computacional.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.perception.manager import SensorManager
from backend.perception.modality import Modality, Percept
from backend.perception.ports import SensorDescriptor, SensorKind
from backend.perception.registry import SensorRegistry
from backend.utils.errors import SensorError, SensorNotFoundError


class FakeStreamingSensor:
    """Sensor de streaming falso que emite 3 percepções."""

    descriptor = SensorDescriptor(
        id="fake-stream",
        modality=Modality.SIGNAL,
        kind=SensorKind.STREAMING,
        name="Fake Streaming",
    )

    def __init__(self) -> None:
        self.opened = False
        self.closed = False

    async def open(self) -> None:
        self.opened = True

    async def close(self) -> None:
        self.closed = True

    async def stream(self) -> AsyncIterator[Percept]:
        for i in range(3):
            yield Percept(
                modality=Modality.SIGNAL, source_id=self.descriptor.id, data=f"p{i}"
            )
            await asyncio.sleep(0)


class FakeOnDemandSensor:
    """Sensor on-demand falso que devolve uma percepção fixa."""

    descriptor = SensorDescriptor(
        id="fake-shot",
        modality=Modality.IMAGE,
        kind=SensorKind.ON_DEMAND,
        name="Fake Shot",
    )

    async def capture(self, **params: object) -> Percept:
        return Percept(
            modality=Modality.IMAGE,
            source_id=self.descriptor.id,
            data=b"bytes",
            mime="image/png",
            metadata=dict(params),
        )


def _registry_with_fakes() -> SensorRegistry:
    registry = SensorRegistry()
    registry.register(FakeStreamingSensor.descriptor, FakeStreamingSensor)
    registry.register(FakeOnDemandSensor.descriptor, FakeOnDemandSensor)
    return registry


async def test_streaming_sensor_flows_to_perceive() -> None:
    """Percepções de um sensor de streaming devem chegar ao fluxo unificado."""
    manager = SensorManager(_registry_with_fakes())
    await manager.activate("fake-stream")
    stream = manager.perceive()
    first = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
    assert first.modality is Modality.SIGNAL
    assert first.data == "p0"
    await manager.aclose()


async def test_on_demand_capture_publishes_percept() -> None:
    """Uma captura on-demand deve retornar e publicar a percepção."""
    manager = SensorManager(_registry_with_fakes())
    percept = await manager.capture("fake-shot", region="full")
    assert percept.modality is Modality.IMAGE
    assert percept.metadata == {"region": "full"}
    published = await asyncio.wait_for(manager.perceive().__anext__(), timeout=1.0)
    assert published.source_id == "fake-shot"


async def test_submit_external_percept() -> None:
    """Percepções de origem externa (cliente remoto) entram pelo mesmo fluxo."""
    manager = SensorManager(SensorRegistry())
    await manager.submit(Percept(modality=Modality.TEXT, source_id="remote", data="oi"))
    got = await asyncio.wait_for(manager.perceive().__anext__(), timeout=1.0)
    assert got.source_id == "remote"


async def test_activate_rejects_on_demand_sensor() -> None:
    """Ativar um sensor on-demand como streaming deve falhar claramente."""
    manager = SensorManager(_registry_with_fakes())
    with pytest.raises(SensorError):
        await manager.activate("fake-shot")


async def test_unknown_sensor_raises() -> None:
    """Descrever/criar sensor inexistente deve levantar SensorNotFoundError."""
    registry = SensorRegistry()
    with pytest.raises(SensorNotFoundError):
        registry.create("nope")


def test_registry_rejects_duplicate() -> None:
    """Registrar o mesmo id duas vezes deve falhar."""
    registry = SensorRegistry()
    registry.register(FakeStreamingSensor.descriptor, FakeStreamingSensor)
    with pytest.raises(ValueError):
        registry.register(FakeStreamingSensor.descriptor, FakeStreamingSensor)


def test_api_lists_sensors() -> None:
    """O endpoint REST deve refletir os sensores registrados no Host."""
    app = create_app()
    with TestClient(app) as tc:  # lifespan cria registry + manager
        assert tc.get("/api/sensors").json() == {"sensors": []}  # vazio na Fase 1
        app.state.sensor_registry.register(
            FakeStreamingSensor.descriptor, FakeStreamingSensor
        )
        body = tc.get("/api/sensors").json()
        assert body["sensors"][0]["id"] == "fake-stream"
        assert body["sensors"][0]["modality"] == "signal"
