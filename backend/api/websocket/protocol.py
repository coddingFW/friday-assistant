"""Protocolo de mensagens do WebSocket de chat.

Define o contrato tipado trocado entre cliente e backend. Manter este contrato
estável é essencial: o frontend (Tauri/React, e futuros clientes) depende dele.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Cliente -> Servidor ----------------------------------------------------


class UserMessage(BaseModel):
    """Mensagem enviada pelo usuário para iniciar uma geração."""

    type: Literal["user_message"] = "user_message"
    content: str = Field(min_length=1, description="Texto do usuário.")
    model: str | None = Field(
        default=None, description="Modelo opcional para sobrescrever o default."
    )


# --- Servidor -> Cliente ----------------------------------------------------

StatusState = Literal["thinking", "searching", "responding", "idle"]


class StatusEvent(BaseModel):
    """Indicador de estado da assistente (ex.: 'Pensando', 'Buscando', 'Respondendo')."""

    type: Literal["status"] = "status"
    state: StatusState


class Source(BaseModel):
    """Fonte usada para embasar a resposta (RAG)."""

    title: str
    url: str


class SourcesEvent(BaseModel):
    """Lista de fontes recuperadas pela busca antes de responder."""

    type: Literal["sources"] = "sources"
    sources: list[Source]


class TokenEvent(BaseModel):
    """Fragmento de texto gerado pelo LLM."""

    type: Literal["token"] = "token"
    content: str


class AudioEvent(BaseModel):
    """Áudio da resposta (TTS) para o cliente reproduzir. Dados em base64."""

    type: Literal["audio"] = "audio"
    mime: str
    data: str  # base64


class DoneEvent(BaseModel):
    """Sinaliza o fim da geração."""

    type: Literal["done"] = "done"


class ErrorEvent(BaseModel):
    """Comunica uma falha ao cliente sem derrubar a conexão."""

    type: Literal["error"] = "error"
    message: str
