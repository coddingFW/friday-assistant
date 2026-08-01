"""Vocabulário de percepção — modalidades e a unidade normalizada :class:`Percept`.

Este módulo define o "idioma" único pelo qual toda entrada sensorial trafega no
sistema, **independente da origem**: um sensor local do Host (microfone, webcam,
captura de tela) ou um cliente remoto (ex.: celular na LAN enviando uma imagem).
Ambos convergem para o mesmo :class:`Percept`, que é o que o Brain enxerga.

Nenhum código de dispositivo ou de visão computacional vive aqui — apenas o
modelo de dados agnóstico de tecnologia.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Modality(str, Enum):
    """Tipos de percepção suportados/planejados pela arquitetura."""

    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"
    SCREEN = "screen"
    OCR_TEXT = "ocr_text"
    SIGNAL = "signal"  # sensores locais genéricos (futuros)


@dataclass(slots=True)
class Percept:
    """Uma unidade normalizada de percepção.

    Attributes:
        modality: A modalidade do dado (texto, áudio, imagem, ...).
        source_id: Identificador do sensor/origem que produziu o percept.
        data: Carga útil — texto (str) ou binário (bytes), conforme a modalidade.
        mime: Tipo MIME opcional (ex.: ``"image/png"``, ``"audio/wav"``).
        timestamp: Época (segundos) de captura.
        metadata: Metadados livres (dimensões, idioma, dispositivo, etc.).
    """

    modality: Modality
    source_id: str
    data: bytes | str
    mime: str | None = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
