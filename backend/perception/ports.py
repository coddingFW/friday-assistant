"""Portas (interfaces) da camada de sensores — Ports & Adapters.

Define os contratos que qualquer sensor futuro deve cumprir. Um sensor concreto
(webcam, captura de tela, OCR, sensor físico) será um *adapter* que implementa
uma destas portas, sem que o Brain jamais dependa da tecnologia do dispositivo.

Dois formatos de percepção são previstos:

* :class:`StreamingSensor` — produz percepções continuamente (microfone, webcam).
* :class:`OnDemandSensor` — produz sob requisição (screenshot, leitura de imagem, OCR).

Nenhuma implementação concreta existe aqui — apenas os contratos.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Protocol, runtime_checkable

from backend.perception.modality import Modality, Percept


class SensorKind(str, Enum):
    """Formato de produção de percepções de um sensor."""

    STREAMING = "streaming"
    ON_DEMAND = "on_demand"


@dataclass(frozen=True, slots=True)
class SensorDescriptor:
    """Metadados que identificam e descrevem um sensor registrável."""

    id: str
    modality: Modality
    kind: SensorKind
    name: str
    description: str = ""


@runtime_checkable
class StreamingSensor(Protocol):
    """Sensor que emite percepções continuamente enquanto ativo."""

    descriptor: SensorDescriptor

    async def open(self) -> None:
        """Inicializa o dispositivo/recurso subjacente."""
        ...

    async def close(self) -> None:
        """Libera o dispositivo/recurso subjacente."""
        ...

    def stream(self) -> AsyncIterator[Percept]:
        """Emite percepções até ser cancelado."""
        ...


@runtime_checkable
class OnDemandSensor(Protocol):
    """Sensor que produz uma percepção a cada requisição explícita."""

    descriptor: SensorDescriptor

    async def capture(self, **params: Any) -> Percept:
        """Captura e retorna uma única percepção."""
        ...


#: Qualquer sensor suportado pela arquitetura.
Sensor = StreamingSensor | OnDemandSensor
