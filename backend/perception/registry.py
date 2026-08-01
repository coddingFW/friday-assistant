"""Registro de sensores — permite adicionar novos sensores sem tocar no núcleo.

Um sensor é registrado como um par (descritor, fábrica). Adicionar uma webcam,
OCR ou qualquer sensor futuro é registrar uma nova entrada aqui (ou via plugin),
sem modificar o Brain, a API ou o gerenciador. Concretiza o requisito de
extensibilidade sem refatoração.
"""

from __future__ import annotations

from typing import Callable

from backend.perception.ports import Sensor, SensorDescriptor
from backend.utils.errors import SensorNotFoundError

#: Fábrica que instancia um sensor sob demanda.
SensorFactory = Callable[[], Sensor]


class SensorRegistry:
    """Catálogo de sensores disponíveis, indexado por identificador."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[SensorDescriptor, SensorFactory]] = {}

    def register(self, descriptor: SensorDescriptor, factory: SensorFactory) -> None:
        """Registra um sensor.

        Raises:
            ValueError: Se o identificador já estiver registrado.
        """
        if descriptor.id in self._entries:
            raise ValueError(f"Sensor já registrado: '{descriptor.id}'.")
        self._entries[descriptor.id] = (descriptor, factory)

    def available(self) -> list[SensorDescriptor]:
        """Lista os descritores de todos os sensores registrados."""
        return [descriptor for descriptor, _ in self._entries.values()]

    def describe(self, sensor_id: str) -> SensorDescriptor:
        """Retorna o descritor de um sensor.

        Raises:
            SensorNotFoundError: Se o sensor não estiver registrado.
        """
        entry = self._entries.get(sensor_id)
        if entry is None:
            raise SensorNotFoundError(f"Sensor não encontrado: '{sensor_id}'.")
        return entry[0]

    def create(self, sensor_id: str) -> Sensor:
        """Instancia um sensor pela sua fábrica.

        Raises:
            SensorNotFoundError: Se o sensor não estiver registrado.
        """
        entry = self._entries.get(sensor_id)
        if entry is None:
            raise SensorNotFoundError(f"Sensor não encontrado: '{sensor_id}'.")
        return entry[1]()
