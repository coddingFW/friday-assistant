"""Camada de percepção — entrada multimodal desacoplada de hardware.

Abrange não só sensores físicos (microfone, webcam, tela), mas também entradas
*derivadas* (OCR, arquivos, imagens) e *remotas* (clientes na LAN). Fornece o
vocabulário de percepção (:class:`Percept`, :class:`Modality`), os contratos de
fonte (Ports & Adapters), o registro extensível e o gerenciador que é a única
fonte de percepção consumida pelo Brain.

Regra invariável: o Brain **nunca** conhece a origem da percepção — toda entrada
externa é convertida em :class:`Percept` normalizado antes de chegar ao núcleo
cognitivo (ADR-0004).

Na Fase 1 esta camada contém **apenas abstrações** — nenhuma fonte concreta e
nenhum código de visão computacional. Fontes reais entram nas fases futuras.
"""

from backend.perception.manager import SensorManager
from backend.perception.modality import Modality, Percept
from backend.perception.ports import (
    OnDemandSensor,
    Sensor,
    SensorDescriptor,
    SensorKind,
    StreamingSensor,
)
from backend.perception.registry import SensorFactory, SensorRegistry

__all__ = [
    "SensorManager",
    "Modality",
    "Percept",
    "Sensor",
    "SensorDescriptor",
    "SensorKind",
    "StreamingSensor",
    "OnDemandSensor",
    "SensorRegistry",
    "SensorFactory",
]
