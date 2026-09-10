"""Provedores de dependência do FastAPI (Dependency Injection).

Centraliza o acesso aos objetos de longa vida guardados em ``app.state`` durante
o lifespan. Os endpoints dependem destas funções — nunca de instâncias globais —
o que mantém tudo testável via ``app.dependency_overrides``.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from backend.brain.conversation import ConversationService
from backend.brain.ports import LLMProvider
from backend.memory.service import MemoryService
from backend.perception.manager import SensorManager
from backend.stt.ports import STTProvider
from backend.workspace.service import WorkspaceService


def get_llm_provider(request: Request) -> LLMProvider:
    """Recupera o provedor de LLM inicializado no lifespan da aplicação.

    Raises:
        HTTPException: 503 se o provedor ainda não foi inicializado.
    """
    provider: LLMProvider | None = getattr(request.app.state, "llm_provider", None)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Provedor de LLM não inicializado.",
        )
    return provider


def get_conversation_service(request: Request) -> ConversationService:
    """Recupera o serviço de conversa (RAG + LLM) inicializado no lifespan.

    Raises:
        HTTPException: 503 se o serviço ainda não foi inicializado.
    """
    service: ConversationService | None = getattr(
        request.app.state, "conversation_service", None
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de conversa não inicializado.",
        )
    return service


def get_memory_service(request: Request) -> MemoryService:
    """Recupera o serviço de memória de longo prazo inicializado no lifespan.

    Raises:
        HTTPException: 503 se a memória estiver desativada ou não inicializada.
    """
    service: MemoryService | None = getattr(
        request.app.state, "memory_service", None
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memória de longo prazo desativada ou não inicializada.",
        )
    return service


def get_workspace_service(request: Request) -> WorkspaceService:
    """Recupera o serviço de workspace (projeto local) do lifespan.

    Raises:
        HTTPException: 503 se o workspace estiver desativado ou não inicializado.
    """
    service: WorkspaceService | None = getattr(
        request.app.state, "workspace_service", None
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workspace desativado ou não inicializado.",
        )
    return service


def get_sensor_manager(request: Request) -> SensorManager:
    """Recupera o gerenciador de sensores inicializado no lifespan.

    Raises:
        HTTPException: 503 se o gerenciador ainda não foi inicializado.
    """
    manager: SensorManager | None = getattr(request.app.state, "sensor_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gerenciador de sensores não inicializado.",
        )
    return manager


def get_stt_provider(request: Request) -> STTProvider:
    """Recupera o provedor de STT inicializado no lifespan.

    Raises:
        HTTPException: 503 se o STT estiver desativado ou não inicializado.
    """
    provider: STTProvider | None = getattr(request.app.state, "stt_provider", None)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Provedor de STT não inicializado (STT desativado?).",
        )
    return provider
