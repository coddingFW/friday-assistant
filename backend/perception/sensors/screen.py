"""Sensor de captura de tela — ``OnDemandSensor`` (Fase 8, visão).

Tira um "screenshot" do Host sob demanda (via ``mss``) e o entrega como um
:class:`Percept` de imagem (PNG). A captura é bloqueante, então roda num worker
thread. O grabber é injetável para permitir testes sem uma tela real.
"""

from __future__ import annotations

import asyncio
from typing import Callable

from backend.perception.modality import Modality, Percept
from backend.perception.ports import SensorDescriptor, SensorKind
from backend.utils.errors import SensorError
from backend.utils.logging import get_logger

logger = get_logger(__name__)

SCREEN_DESCRIPTOR = SensorDescriptor(
    id="screen",
    modality=Modality.SCREEN,
    kind=SensorKind.ON_DEMAND,
    name="Tela",
    description="Captura a tela do Host (screenshot) como imagem PNG.",
)


def _grab_png(monitor: int) -> bytes:
    """Captura a tela via mss e devolve os bytes PNG (bloqueante)."""
    try:
        import mss
        import mss.tools
    except (ImportError, OSError) as exc:  # pragma: no cover - ambiente sem mss
        raise SensorError(f"mss indisponível para capturar a tela: {exc}") from exc
    try:
        with mss.mss() as sct:
            region = sct.monitors[monitor]
            shot = sct.grab(region)
            return mss.tools.to_png(shot.rgb, shot.size)
    except Exception as exc:  # noqa: BLE001 - traduz falha de captura
        raise SensorError(f"Falha ao capturar a tela: {exc}") from exc


class ScreenCaptureSensor:
    """``OnDemandSensor`` que captura a tela do Host como imagem."""

    descriptor = SCREEN_DESCRIPTOR

    def __init__(
        self,
        *,
        monitor: int = 1,
        grabber: Callable[[], bytes] | None = None,
    ) -> None:
        self._monitor = monitor
        self._grabber = grabber

    async def capture(self, **_params: object) -> Percept:
        """Captura a tela (no worker thread) e devolve um Percept de imagem PNG."""
        grab = self._grabber or (lambda: _grab_png(self._monitor))
        png = await asyncio.to_thread(grab)
        logger.info("screen_captured", bytes=len(png), monitor=self._monitor)
        return Percept(
            modality=Modality.SCREEN,
            source_id=self.descriptor.id,
            data=png,
            mime="image/png",
            metadata={"monitor": self._monitor},
        )
