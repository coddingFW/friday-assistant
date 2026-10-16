"""Ponto de entrada do backend Friday (FastAPI).

Responsabilidades:
    * configurar logging e configuração;
    * gerenciar o ciclo de vida do cliente HTTP e do provedor de LLM (lifespan);
    * montar as rotas REST e WebSocket;
    * expor ``app`` para o Uvicorn (``uvicorn backend.main:app``).
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import __version__
from backend.api.rest import router as rest_router
from backend.api.websocket import router as ws_router
from backend.brain.conversation import ConversationService
from backend.brain.factory import create_llm_provider
from backend.config.settings import Settings, get_settings
from backend.memory.factory import create_conversation_repository
from backend.memory.service import MemoryService
from backend.workspace.factory import create_workspace_provider
from backend.workspace.service import WorkspaceService
from backend.perception.manager import SensorManager
from backend.perception.registry import SensorRegistry
from backend.perception.sensors.microphone import (
    MICROPHONE_DESCRIPTOR,
    MicrophoneSensor,
)
from backend.perception.sensors.ocr import OCR_DESCRIPTOR, OcrSensor
from backend.perception.sensors.screen import SCREEN_DESCRIPTOR, ScreenCaptureSensor
from backend.rag.factory import create_search_provider
from backend.rag.service import RagService
from backend.stt.factory import create_stt_provider
from backend.tts.factory import create_tts_provider
from backend.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


def _build_http_client(settings: Settings) -> httpx.AsyncClient:
    """Cria o cliente HTTP compartilhado apontado para o serviço de LLM."""
    timeout = httpx.Timeout(
        settings.ollama_read_timeout,
        connect=settings.ollama_connect_timeout,
    )
    return httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=timeout)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Inicializa e encerra recursos de longa vida (DI raiz da aplicação)."""
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)

    client = _build_http_client(settings)
    app.state.http_client = client
    app.state.llm_provider = create_llm_provider(settings, client)

    # RAG + TTS + orquestração de conversa (caso de uso central do diálogo).
    rag_service = RagService(create_search_provider(settings), settings)
    tts_provider = create_tts_provider(settings)
    app.state.conversation_service = ConversationService(
        app.state.llm_provider, rag_service, settings, tts=tts_provider
    )

    # Memória de longo prazo (Fase 9): persiste conversas em SQLite. Desativável
    # por config; falha ao abrir degrada para só-RAM (não derruba o startup).
    app.state.memory_repository = None
    app.state.memory_service = None
    if settings.memory_enabled:
        try:
            repository = create_conversation_repository(settings)
            app.state.memory_repository = repository
            app.state.memory_service = MemoryService(repository)
        except Exception as exc:  # noqa: BLE001 - degrada sem memória persistente
            logger.warning("memory_init_failed", error=str(exc))

    # Workspace de código (Fase 10): acesso de LEITURA a um projeto local. A raiz
    # começa vazia; o usuário aponta a pasta pela UI (REST). Desativável por config.
    app.state.workspace_service = None
    if settings.workspace_enabled:
        app.state.workspace_service = WorkspaceService(
            create_workspace_provider(settings),
            context_char_budget=settings.workspace_context_char_budget,
        )

    # Camada de percepção multimodal. Na Fase 6 registramos o primeiro sensor
    # concreto — o microfone — quando o STT está ativo.
    registry = SensorRegistry()
    app.state.stt_provider = None
    if settings.stt_enabled:
        app.state.stt_provider = create_stt_provider(settings)
        registry.register(
            MICROPHONE_DESCRIPTOR,
            lambda: MicrophoneSensor(
                sample_rate=settings.mic_sample_rate,
                frame_ms=settings.mic_frame_ms,
                silence_ms=settings.mic_silence_ms,
                energy_threshold=settings.mic_energy_threshold,
                min_speech_ms=settings.mic_min_speech_ms,
                max_utterance_ms=settings.mic_max_utterance_ms,
            ),
        )
    if settings.vision_enabled:
        registry.register(SCREEN_DESCRIPTOR, lambda: ScreenCaptureSensor())
        if settings.ocr_enabled:
            registry.register(
                OCR_DESCRIPTOR,
                lambda: OcrSensor(
                    lang=settings.ocr_lang,
                    tesseract_cmd=settings.ocr_tesseract_cmd,
                    tessdata_dir=settings.ocr_tessdata_dir,
                ),
            )
    app.state.sensor_registry = registry
    app.state.sensor_manager = SensorManager(registry)

    logger.info(
        "backend_startup",
        provider=settings.llm_provider,
        model=settings.llm_model,
        ollama=settings.ollama_base_url,
        rag_enabled=settings.rag_enabled,
        rag_provider=settings.rag_provider,
        memory_enabled=settings.memory_enabled and app.state.memory_service is not None,
        workspace_enabled=app.state.workspace_service is not None,
        code_model=settings.code_model,
        tts_enabled=settings.tts_enabled,
        tts_provider=settings.tts_provider,
        stt_enabled=settings.stt_enabled,
        stt_model=settings.whisper_model if settings.stt_enabled else None,
        vision_enabled=settings.vision_enabled,
        vision_model=settings.vision_model if settings.vision_enabled else None,
        ocr_enabled=settings.vision_enabled and settings.ocr_enabled,
        sensors=len(app.state.sensor_registry.available()),
        warmup=settings.ollama_warmup,
    )

    # Warm-up opcional do modelo, em segundo plano — não bloqueia o startup.
    warmup_task: asyncio.Task[bool] | None = None
    provider = app.state.llm_provider
    if settings.ollama_warmup and hasattr(provider, "warmup"):
        warmup_task = asyncio.create_task(provider.warmup(), name="ollama-warmup")

    try:
        yield
    finally:
        if warmup_task is not None:
            warmup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await warmup_task
        await app.state.sensor_manager.aclose()
        if app.state.memory_repository is not None:
            with contextlib.suppress(Exception):
                await app.state.memory_repository.close()
        await client.aclose()
        logger.info("backend_shutdown")


def create_app() -> FastAPI:
    """Cria e configura a instância do FastAPI (application factory)."""
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)

    app = FastAPI(
        title="Friday — Backend",
        version=__version__,
        summary="Backend local da Assistente Virtual Friday.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(rest_router, prefix="/api")
    app.include_router(ws_router)
    return app


app = create_app()
