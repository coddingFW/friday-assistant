"""WebSocket de chat: streaming de respostas do LLM (com RAG) em tempo real.

Fluxo por turno:
    cliente envia  {"type": "user_message", "content": "..."}
    servidor emite {"type": "status", "state": "thinking"}
                   {"type": "status", "state": "searching"}   (se RAG ativo)
                   {"type": "sources", "sources": [...]}       (se houver fontes)
                   {"type": "status", "state": "responding"}
                   {"type": "token", "content": "..."}         (N vezes)
                   {"type": "done"}
                   {"type": "status", "state": "idle"}
Em caso de falha, emite {"type": "error", "message": "..."} e mantém a conexão.

Esta camada é fina: apenas traduz eventos de domínio (:mod:`backend.brain.events`)
para o protocolo do cliente. Toda a regra de negócio vive no ConversationService.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

import base64

from backend.api.websocket.protocol import (
    AudioEvent,
    DoneEvent,
    ErrorEvent,
    Source,
    SourcesEvent,
    StatusEvent,
    TokenEvent,
    UserMessage,
)
from backend.brain.conversation import ConversationService
from backend.brain.events import (
    AudioReady,
    GenerationFailed,
    SourcesGathered,
    StatusChanged,
    TokenGenerated,
    TurnCompleted,
)
from backend.brain.ports import ChatMessage
from backend.config.settings import get_settings
from backend.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket) -> None:
    """Endpoint WebSocket que transmite a resposta (RAG + LLM) token a token."""
    service: ConversationService | None = getattr(
        websocket.app.state, "conversation_service", None
    )
    await websocket.accept()

    if service is None:
        await websocket.send_json(
            ErrorEvent(message="Serviço de conversa não inicializado.").model_dump()
        )
        await websocket.close()
        return

    logger.info("ws_chat_connected")
    # Memória de curto prazo da conversa: vive na conexão (o ConversationService
    # é um singleton compartilhado e permanece stateless). Persistência entre
    # sessões é a Fase 9.
    history: list[ChatMessage] = []
    try:
        while True:
            raw = await websocket.receive_json()
            try:
                message = UserMessage.model_validate(raw)
            except ValidationError as exc:
                await websocket.send_json(
                    ErrorEvent(message=f"Mensagem inválida: {exc.errors()}").model_dump()
                )
                continue

            await _handle_turn(websocket, service, message, history)
    except WebSocketDisconnect:
        logger.info("ws_chat_disconnected")


async def _handle_turn(
    websocket: WebSocket,
    service: ConversationService,
    message: UserMessage,
    history: list[ChatMessage],
) -> None:
    """Consome os eventos de domínio de um turno e os envia ao cliente.

    Acumula a resposta do assistente para, ao final de um turno bem-sucedido,
    memorizá-la em ``history`` (contexto do próximo turno). Resiliente à
    desconexão do cliente no meio do streaming: se o envio falhar (socket
    fechado), aborta o turno e fecha o gerador — o que propaga o cancelamento
    até o stream do LLM, evitando geração órfã e sem gravar resposta parcial.
    """
    events = service.run(message.content, model=message.model, history=history)
    answer_parts: list[str] = []
    failed = False
    try:
        async for event in events:
            if isinstance(event, TokenGenerated):
                answer_parts.append(event.text)
            elif isinstance(event, GenerationFailed):
                failed = True
            payload = _to_protocol(event)
            if payload is not None:
                await websocket.send_json(payload)
    except (WebSocketDisconnect, RuntimeError):
        logger.info("ws_chat_turn_aborted")
        return
    finally:
        await events.aclose()

    answer = "".join(answer_parts)
    if not failed and answer:
        _remember(history, message.content, answer)


def _remember(history: list[ChatMessage], user_text: str, answer: str) -> None:
    """Adiciona o par (usuário, assistente) ao histórico, aparando o excedente.

    Mantém apenas as últimas ``history_max_messages`` mensagens para limitar o
    tamanho do prompt; ``0`` desativa a memória de conversa.
    """
    history.append(ChatMessage(role="user", content=user_text))
    history.append(ChatMessage(role="assistant", content=answer))
    limit = get_settings().history_max_messages
    if len(history) > limit:
        del history[: len(history) - limit]


def _to_protocol(event: object) -> dict | None:
    """Traduz um evento de domínio para uma mensagem do protocolo do cliente."""
    if isinstance(event, StatusChanged):
        return StatusEvent(state=event.state).model_dump()
    if isinstance(event, SourcesGathered):
        return SourcesEvent(
            sources=[Source(title=s.title, url=s.url) for s in event.sources]
        ).model_dump()
    if isinstance(event, TokenGenerated):
        return TokenEvent(content=event.text).model_dump()
    if isinstance(event, AudioReady):
        return AudioEvent(
            mime=event.mime, data=base64.b64encode(event.data).decode("ascii")
        ).model_dump()
    if isinstance(event, TurnCompleted):
        return DoneEvent().model_dump()
    if isinstance(event, GenerationFailed):
        return ErrorEvent(message=event.message).model_dump()
    return None
