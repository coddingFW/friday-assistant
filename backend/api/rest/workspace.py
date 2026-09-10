"""Endpoints REST do workspace (Fase 10) — projeto local, somente leitura.

Apontar a pasta do projeto, listar a árvore, ler um arquivo e buscar no código.
Enviar mensagens (que usam esses arquivos como contexto) continua no WebSocket.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.api.dependencies import get_workspace_service
from backend.utils.errors import WorkspaceError
from backend.workspace.service import WorkspaceService


class RootRequest(BaseModel):
    """Pasta do projeto a abrir (caminho absoluto no Host)."""

    path: str


class RootResponse(BaseModel):
    """Raiz atualmente aberta (ou ``None``)."""

    root: str | None


class TreeEntryOut(BaseModel):
    path: str
    name: str
    is_dir: bool
    size: int


class FileResponse(BaseModel):
    path: str
    text: str
    truncated: bool
    size: int


class SearchHitOut(BaseModel):
    path: str
    line: int
    text: str


class WriteRequest(BaseModel):
    """Escrita de um arquivo do projeto (iniciada e confirmada pelo usuário)."""

    path: str
    text: str


class WriteResultOut(BaseModel):
    path: str
    created: bool
    bytes_written: int
    backup_path: str | None


router = APIRouter()


@router.get("/workspace/root", response_model=RootResponse, summary="Raiz atual")
async def get_root(
    ws: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> RootResponse:
    """Devolve a pasta de projeto atualmente aberta."""
    return RootResponse(root=ws.root)


@router.post("/workspace/root", response_model=RootResponse, summary="Abre uma pasta")
async def set_root(
    body: RootRequest,
    ws: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> RootResponse:
    """Define a pasta do projeto (valida que existe e é diretório)."""
    try:
        root = await ws.set_root(body.path)
    except WorkspaceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return RootResponse(root=root)


@router.get(
    "/workspace/tree", response_model=list[TreeEntryOut], summary="Árvore de arquivos"
)
async def get_tree(
    ws: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> list[TreeEntryOut]:
    """Lista arquivos e pastas do projeto (ignorando ruído)."""
    try:
        entries = await ws.tree()
    except WorkspaceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return [
        TreeEntryOut(path=e.path, name=e.name, is_dir=e.is_dir, size=e.size)
        for e in entries
    ]


@router.get("/workspace/file", response_model=FileResponse, summary="Lê um arquivo")
async def read_file(
    path: str,
    ws: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> FileResponse:
    """Lê um arquivo de texto do projeto (confinado à raiz)."""
    try:
        fc = await ws.read_file(path)
    except WorkspaceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return FileResponse(path=fc.path, text=fc.text, truncated=fc.truncated, size=fc.size)


@router.post(
    "/workspace/file", response_model=WriteResultOut, summary="Escreve um arquivo"
)
async def write_file(
    body: WriteRequest,
    ws: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WriteResultOut:
    """Escreve/edita um arquivo de texto do projeto (confinado, com backup).

    A escrita é sempre iniciada e confirmada pelo usuário no cliente; o backend
    só a executa quando permitida por configuração e confinada à raiz.
    """
    try:
        result = await ws.write_file(body.path, body.text)
    except WorkspaceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return WriteResultOut(
        path=result.path,
        created=result.created,
        bytes_written=result.bytes_written,
        backup_path=result.backup_path,
    )


@router.get(
    "/workspace/search", response_model=list[SearchHitOut], summary="Busca no código"
)
async def search(
    q: str,
    ws: Annotated[WorkspaceService, Depends(get_workspace_service)],
    max_hits: int = 100,
) -> list[SearchHitOut]:
    """Busca textual simples nos arquivos de texto do projeto."""
    try:
        hits = await ws.search(q, max_hits=max_hits)
    except WorkspaceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return [SearchHitOut(path=h.path, line=h.line, text=h.text) for h in hits]
