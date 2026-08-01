"""Gerenciador de sensores — ponto único de convergência das percepções.

Este é o **único** objeto do qual o Brain depende para "perceber". Ele:

* ativa/desativa sensores de streaming, bombeando suas percepções para uma fila;
* aciona capturas sob demanda;
* aceita percepções de origem externa (ex.: upload de um cliente remoto) via
  :meth:`submit`, normalizadas no mesmo :class:`Percept`.

Assim, o Brain nunca acessa um dispositivo físico: ele apenas consome de
:meth:`perceive`. Trocar/adicionar sensores não altera o Brain (baixo acoplamento).
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import AsyncIterator

from backend.perception.modality import Percept
from backend.perception.ports import SensorDescriptor, SensorKind, StreamingSensor
from backend.perception.registry import SensorRegistry
from backend.utils.errors import SensorError
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class SensorManager:
    """Orquestra sensores e expõe um fluxo unificado de percepções ao domínio."""

    def __init__(self, registry: SensorRegistry, *, queue_size: int = 256) -> None:
        self._registry = registry
        self._queue: asyncio.Queue[Percept] = asyncio.Queue(maxsize=queue_size)
        self._active: dict[str, tuple[StreamingSensor, asyncio.Task[None]]] = {}

    def available(self) -> list[SensorDescriptor]:
        """Lista os sensores registrados (disponíveis para ativação)."""
        return self._registry.available()

    async def activate(self, sensor_id: str) -> None:
        """Ativa um sensor de streaming e passa a coletar suas percepções.

        Raises:
            SensorError: Se o sensor não for do tipo streaming.
            SensorNotFoundError: Se o sensor não estiver registrado.
        """
        if sensor_id in self._active:
            return
        descriptor = self._registry.describe(sensor_id)
        if descriptor.kind is not SensorKind.STREAMING:
            raise SensorError(
                f"Sensor '{sensor_id}' é on-demand; use capture()."
            )
        sensor = self._registry.create(sensor_id)
        await sensor.open()  # type: ignore[union-attr]
        task = asyncio.create_task(self._pump(sensor), name=f"sensor:{sensor_id}")
        self._active[sensor_id] = (sensor, task)  # type: ignore[assignment]
        logger.info("sensor_activated", sensor=sensor_id)

    async def deactivate(self, sensor_id: str) -> None:
        """Desativa um sensor de streaming e libera seus recursos."""
        entry = self._active.pop(sensor_id, None)
        if entry is None:
            return
        sensor, task = entry
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await sensor.close()
        logger.info("sensor_deactivated", sensor=sensor_id)

    async def capture(self, sensor_id: str, **params: object) -> Percept:
        """Aciona uma captura pontual em um sensor on-demand e a publica.

        Raises:
            SensorError: Se o sensor não for do tipo on-demand.
        """
        descriptor = self._registry.describe(sensor_id)
        if descriptor.kind is not SensorKind.ON_DEMAND:
            raise SensorError(
                f"Sensor '{sensor_id}' é de streaming; use activate()."
            )
        sensor = self._registry.create(sensor_id)
        percept = await sensor.capture(**params)  # type: ignore[union-attr]
        await self._queue.put(percept)
        return percept

    async def submit(self, percept: Percept) -> None:
        """Injeta uma percepção de origem externa (ex.: cliente remoto na LAN)."""
        await self._queue.put(percept)

    async def perceive(self) -> AsyncIterator[Percept]:
        """Fluxo unificado de percepções — a única entrada sensorial do Brain."""
        while True:
            yield await self._queue.get()

    async def _pump(self, sensor: StreamingSensor) -> None:
        """Transfere as percepções de um sensor de streaming para a fila."""
        try:
            async for percept in sensor.stream():
                await self._queue.put(percept)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - isola falhas de um sensor
            logger.warning(
                "sensor_stream_error", sensor=sensor.descriptor.id, error=str(exc)
            )

    async def aclose(self) -> None:
        """Desativa todos os sensores ativos (encerramento gracioso)."""
        for sensor_id in list(self._active):
            await self.deactivate(sensor_id)
