"""WebSocket de chat: streaming de respostas do LLM (com RAG) e escuta por voz.

Fluxo por turno (texto):
    cliente envia  {"type": "user_message", "content": "..."}
    servidor emite {"type": "status", "state": "thinking"}
                   {"type": "status", "state": "searching"}   (se RAG ativo)
                   {"type": "sources", "sources": [...]}       (se houver fontes)
                   {"type": "status", "state": "responding"}
                   {"type": "token", "content": "..."}         (N vezes)
                   {"type": "done"}
                   {"type": "status", "state": "idle"}

Fluxo de voz (STT — Fase 6):
    cliente envia  {"type": "listen_start"}
    servidor emite {"type": "status", "state": "listening"}
                   {"type": "transcript", "text": "...", "final": true}   (por fala)
    cliente envia  {"type": "listen_stop"}
                   {"type": "status", "state": "idle"}
O cliente decide o que fazer com a transcrição (auto-enviar ou preencher o campo).

Em caso de falha, emite {"type": "error", "message": "..."} e mantém a conexão.
Esta camada é fina: traduz eventos de domínio para o protocolo do cliente; a
regra de negócio vive no ConversationService e na camada de percepção.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from backend.api.websocket.protocol import (
    AudioEvent,
    ConversationEvent,
    DoneEvent,
    ErrorEvent,
    Source,
    SourcesEvent,
    StatusEvent,
    TokenEvent,
    TranscriptEvent,
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
from backend.memory.service import MemoryService
from backend.perception.manager import SensorManager
from backend.perception.modality import Modality
from backend.perception.sensors.microphone import MICROPHONE_DESCRIPTOR
from backend.stt.ports import STTProvider
from backend.utils.errors import STTError, StorageError, WorkspaceError
from backend.workspace.service import WorkspaceService
from backend.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

_MIC_ID = MICROPHONE_DESCRIPTOR.id


@router.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket) -> None:
    """Transmite respostas (RAG + LLM) e transcreve voz do microfone (STT)."""
    state = websocket.app.state
    service: ConversationService | None = getattr(state, "conversation_service", None)
    sensor_manager: SensorManager | None = getattr(state, "sensor_manager", None)
    stt: STTProvider | None = getattr(state, "stt_provider", None)
    memory: MemoryService | None = getattr(state, "memory_service", None)
    workspace: WorkspaceService | None = getattr(state, "workspace_service", None)

    await websocket.accept()
    if service is None:
        await websocket.send_json(
            ErrorEvent(message="Serviço de conversa não inicializado.").model_dump()
        )
        await websocket.close()
        return

    logger.info("ws_chat_connected")
    # Estado por conexão. ``history`` é a janela de contexto do LLM (curto prazo,
    # em RAM); com memória de longo prazo ativa, ela é semeada do banco e cada
    # turno também é persistido (Fase 9). O ConversationService é singleton e
    # permanece stateless. O lock serializa os envios: turno e escuta rodam
    # concorrentes e não podem escrever ao mesmo tempo no mesmo socket.
    history: list[ChatMessage] = []
    conversation_id: str | None = None
    send_lock = asyncio.Lock()
    listen_task: asyncio.Task[None] | None = None

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type") if isinstance(raw, dict) else None

            if msg_type == "listen_start":
                listen_task = await _start_listening(
                    websocket, send_lock, sensor_manager, stt, listen_task
                )
            elif msg_type == "listen_stop":
                await _stop_listening(websocket, send_lock, sensor_manager, listen_task)
                listen_task = None
            else:
                try:
                    message = UserMessage.model_validate(raw)
                except ValidationError as exc:
                    await _send(
                        websocket,
                        send_lock,
                        ErrorEvent(message=f"Mensagem inválida: {exc.errors()}").model_dump(),
                    )
                    continue
                if memory is not None:
                    conversation_id = await _ensure_conversation(
                        websocket, send_lock, memory, message, conversation_id, history
                    )
                # Turno de código: lê os arquivos do projeto pedidos como contexto.
                context_blocks: list[str] = []
                if workspace is not None and message.context_files:
                    try:
                        context_blocks = await workspace.build_context_blocks(
                            message.context_files
                        )
                    except WorkspaceError as exc:
                        await _send(
                            websocket,
                            send_lock,
                            ErrorEvent(
                                message=f"Falha ao ler arquivos do projeto: {exc}"
                            ).model_dump(),
                        )
                await _handle_turn(
                    websocket,
                    send_lock,
                    service,
                    message,
                    history,
                    memory,
                    conversation_id,
                    context_blocks,
                )
    except WebSocketDisconnect:
        logger.info("ws_chat_disconnected")
    finally:
        # Encerra a escuta e libera o microfone se a conexão cair no meio.
        if listen_task is not None and not listen_task.done():
            listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await listen_task
        if sensor_manager is not None:
            with contextlib.suppress(Exception):
                await sensor_manager.deactivate(_MIC_ID)


async def _send(websocket: WebSocket, send_lock: asyncio.Lock, payload: dict) -> None:
    """Envia um payload JSON serializando com o lock da conexão."""
    async with send_lock:
        await websocket.send_json(payload)


# --- Turno de conversa ------------------------------------------------------


async def _handle_turn(
    websocket: WebSocket,
    send_lock: asyncio.Lock,
    service: ConversationService,
    message: UserMessage,
    history: list[ChatMessage],
    memory: MemoryService | None,
    conversation_id: str | None,
    context_blocks: list[str],
) -> None:
    """Consome os eventos de domínio de um turno e os envia ao cliente.

    Acumula a resposta do assistente para, ao final de um turno bem-sucedido,
    memorizá-la em ``history`` (curto prazo) e persisti-la na memória de longo
    prazo, quando ativa. Resiliente à desconexão do cliente no meio do streaming:
    se o envio falhar, aborta o turno e fecha o gerador (propaga o cancelamento
    até o LLM), sem gravar resposta parcial.
    """
    events = service.run(
        message.content,
        model=message.model,
        history=history,
        images=message.images,
        context_blocks=context_blocks,
    )
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
                await _send(websocket, send_lock, payload)
    except (WebSocketDisconnect, RuntimeError):
        logger.info("ws_chat_turn_aborted")
        return
    finally:
        await events.aclose()

    answer = "".join(answer_parts)
    if not failed and answer:
        _remember(history, message.content, answer)
        if memory is not None and conversation_id is not None:
            # Persiste o turno. Falha de disco degrada graciosamente: o turno já
            # foi entregue ao cliente e continua na memória de curto prazo.
            try:
                await memory.record_turn(
                    conversation_id, message.content, answer, model=message.model
                )
            except StorageError as exc:
                logger.warning("memory_record_turn_failed", error=str(exc))


async def _ensure_conversation(
    websocket: WebSocket,
    send_lock: asyncio.Lock,
    memory: MemoryService,
    message: UserMessage,
    current_id: str | None,
    history: list[ChatMessage],
) -> str | None:
    """Resolve a conversa ativa antes de um turno (memória de longo prazo).

    - ``conversation_id`` da mensagem igual à atual → mantém, nada a fazer.
    - ``conversation_id`` existente → retoma: semeia ``history`` com a janela do
      banco e anuncia a conversa ao cliente.
    - sem ``conversation_id`` e já há conversa atual → continua nela.
    - caso contrário (1ª mensagem, ou id inexistente) → cria uma conversa nova.

    Degrada graciosamente: se o banco falhar, loga e devolve a conversa atual —
    o turno segue apenas na memória de curto prazo.
    """
    requested = message.conversation_id
    try:
        if requested is not None and requested == current_id:
            return current_id
        if requested is not None:
            conv = await memory.get_conversation(requested)
            if conv is not None:
                limit = get_settings().history_max_messages
                window = await memory.history_window(conv.id, limit=limit)
                history[:] = window
                await _send(
                    websocket,
                    send_lock,
                    ConversationEvent(id=conv.id, title=conv.title).model_dump(),
                )
                return conv.id
            # id pedido não existe: cai para criar uma conversa nova.
        elif current_id is not None:
            return current_id

        conv = await memory.start_conversation(message.content)
        history.clear()
        await _send(
            websocket,
            send_lock,
            ConversationEvent(id=conv.id, title=conv.title).model_dump(),
        )
        return conv.id
    except StorageError as exc:
        logger.warning("memory_ensure_conversation_failed", error=str(exc))
        return current_id


def _remember(history: list[ChatMessage], user_text: str, answer: str) -> None:
    """Adiciona o par (usuário, assistente) ao histórico, aparando o excedente."""
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


# --- Escuta por voz (STT) ---------------------------------------------------


async def _start_listening(
    websocket: WebSocket,
    send_lock: asyncio.Lock,
    manager: SensorManager | None,
    stt: STTProvider | None,
    existing: asyncio.Task[None] | None,
) -> asyncio.Task[None] | None:
    """Inicia (idempotente) a escuta do microfone, retornando a task ativa."""
    if existing is not None and not existing.done():
        return existing
    if manager is None or stt is None:
        await _send(
            websocket,
            send_lock,
            ErrorEvent(message="Transcrição de voz indisponível (STT desativado).").model_dump(),
        )
        return None
    return asyncio.create_task(
        _listen_loop(websocket, send_lock, manager, stt), name="stt-listen"
    )


async def _stop_listening(
    websocket: WebSocket,
    send_lock: asyncio.Lock,
    manager: SensorManager | None,
    listen_task: asyncio.Task[None] | None,
) -> None:
    """Encerra a escuta, libera o microfone e volta ao estado ocioso."""
    if listen_task is not None and not listen_task.done():
        listen_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listen_task
    elif manager is not None:
        with contextlib.suppress(Exception):
            await manager.deactivate(_MIC_ID)
    await _send(websocket, send_lock, StatusEvent(state="idle").model_dump())


async def _listen_loop(
    websocket: WebSocket,
    send_lock: asyncio.Lock,
    manager: SensorManager,
    stt: STTProvider,
) -> None:
    """Ativa o microfone, transcreve cada fala e envia a transcrição ao cliente."""
    try:
        await manager.activate(_MIC_ID)
    except Exception as exc:  # noqa: BLE001 - traduz falha de ativação/dispositivo
        logger.warning("stt_activate_error", error=str(exc))
        await _send(
            websocket,
            send_lock,
            ErrorEvent(message=f"Não foi possível abrir o microfone: {exc}").model_dump(),
        )
        return

    await _send(websocket, send_lock, StatusEvent(state="listening").model_dump())
    try:
        async for percept in manager.perceive():
            if percept.modality is not Modality.AUDIO:
                continue
            data = percept.data if isinstance(percept.data, bytes) else b""
            if not data:
                continue
            sample_rate = int(percept.metadata.get("sample_rate", 16000))
            try:
                transcript = await stt.transcribe(data, sample_rate=sample_rate)
            except STTError as exc:
                logger.warning("stt_transcribe_error", error=str(exc))
                continue
            if transcript.text:
                await _send(
                    websocket,
                    send_lock,
                    TranscriptEvent(text=transcript.text, final=True).model_dump(),
                )
    except asyncio.CancelledError:
        raise
    finally:
        with contextlib.suppress(Exception):
            await manager.deactivate(_MIC_ID)
