"""Eventos de domínio de um turno de conversa.

O :class:`ConversationService` emite estes eventos; a camada de transporte
(WebSocket) os traduz para o protocolo do cliente. Manter os eventos separados
do protocolo de rede preserva o domínio testável e agnóstico de transporte.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TurnState = Literal["thinking", "searching", "responding", "idle"]


@dataclass(frozen=True, slots=True)
class SourceRef:
    """Referência a uma fonte usada para embasar a resposta."""

    title: str
    url: str


@dataclass(frozen=True, slots=True)
class StatusChanged:
    """Mudança de estado da assistente durante o turno."""

    state: TurnState


@dataclass(frozen=True, slots=True)
class SourcesGathered:
    """Fontes recuperadas pela busca (RAG)."""

    sources: list[SourceRef]


@dataclass(frozen=True, slots=True)
class TokenGenerated:
    """Fragmento de texto gerado pelo LLM."""

    text: str


@dataclass(frozen=True, slots=True)
class AudioReady:
    """Áudio da resposta sintetizado (TTS), pronto para o cliente reproduzir."""

    data: bytes
    mime: str


@dataclass(frozen=True, slots=True)
class TurnCompleted:
    """A geração do turno terminou com sucesso."""


@dataclass(frozen=True, slots=True)
class GenerationFailed:
    """A geração falhou; carrega a mensagem de erro."""

    message: str


ConversationEvent = (
    StatusChanged
    | SourcesGathered
    | TokenGenerated
    | AudioReady
    | TurnCompleted
    | GenerationFailed
)
