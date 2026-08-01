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
from backend.perception.manager import SensorManager
from backend.perception.registry import SensorRegistry
from backend.rag.factory import create_search_provider
from backend.rag.service import RagService
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

    # RAG + orquestração de conversa (caso de uso central do diálogo).
    rag_service = RagService(create_search_provider(settings), settings)
    app.state.conversation_service = ConversationService(
        app.state.llm_provider, rag_service, settings
    )

    # Camada de percepção multimodal. Registro vazio na Fase 1 — sensores
    # concretos são registrados nas fases futuras, sem alterar este núcleo.
    app.state.sensor_registry = SensorRegistry()
    app.state.sensor_manager = SensorManager(app.state.sensor_registry)

    logger.info(
        "backend_startup",
        provider=settings.llm_provider,
        model=settings.llm_model,
        ollama=settings.ollama_base_url,
        rag_enabled=settings.rag_enabled,
        rag_provider=settings.rag_provider,
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
