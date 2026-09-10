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
    images: list[str] = Field(
        default_factory=list,
        description="Imagens em base64 (sem prefixo data:) para o LLM de visão.",
    )
    conversation_id: str | None = Field(
        default=None,
        description=(
            "Conversa a retomar (memória de longo prazo). Ausente = continua a "
            "conversa atual da conexão, ou cria uma nova na primeira mensagem."
        ),
    )
    context_files: list[str] = Field(
        default_factory=list,
        description=(
            "Arquivos do projeto (caminhos relativos à raiz do workspace) a "
            "incluir como contexto. Não vazio = turno de código: usa o modelo de "
            "código e o prompt de ensino, e pula a busca web."
        ),
    )


class ListenStart(BaseModel):
    """Pede para iniciar a escuta do microfone (STT)."""

    type: Literal["listen_start"] = "listen_start"


class ListenStop(BaseModel):
    """Pede para encerrar a escuta do microfone (STT)."""

    type: Literal["listen_stop"] = "listen_stop"


# --- Servidor -> Cliente ----------------------------------------------------

StatusState = Literal["thinking", "searching", "responding", "idle", "listening"]


class StatusEvent(BaseModel):
    """Indicador de estado da assistente (ex.: 'Pensando', 'Buscando', 'Respondendo')."""

    type: Literal["status"] = "status"
    state: StatusState


class ConversationEvent(BaseModel):
    """Anuncia a conversa ativa (criada ou retomada) para o cliente.

    Emitido quando o backend cria uma conversa nova ou passa a atender uma
    ``conversation_id`` diferente, para o cliente conhecer o id (memória longa).
    """

    type: Literal["conversation"] = "conversation"
    id: str
    title: str


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


class TranscriptEvent(BaseModel):
    """Transcrição de uma fala captada pelo microfone (STT)."""

    type: Literal["transcript"] = "transcript"
    text: str
    final: bool = True


class DoneEvent(BaseModel):
    """Sinaliza o fim da geração."""

    type: Literal["done"] = "done"


class ErrorEvent(BaseModel):
    """Comunica uma falha ao cliente sem derrubar a conexão."""

    type: Literal["error"] = "error"
    message: str
