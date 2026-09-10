"""Portas (interfaces) da camada de workspace — Ports & Adapters.

O domínio depende apenas destas abstrações. O adapter concreto (leitura do
sistema de arquivos local) implementa :class:`WorkspaceProvider`. Toda operação é
confinada à raiz escolhida pelo usuário; sair dela é erro, nunca silêncio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class TreeEntry:
    """Uma entrada da árvore do projeto (caminho relativo à raiz)."""

    path: str  # relativo à raiz, com "/" como separador
    name: str
    is_dir: bool
    size: int = 0  # bytes (0 para diretórios)


@dataclass(frozen=True, slots=True)
class FileContent:
    """Conteúdo textual de um arquivo do projeto."""

    path: str  # relativo à raiz
    text: str
    truncated: bool  # True se cortado pelo limite de tamanho
    size: int  # bytes do arquivo original


@dataclass(frozen=True, slots=True)
class SearchHit:
    """Uma ocorrência de busca textual no projeto."""

    path: str
    line: int  # 1-based
    text: str  # a linha casada (aparada)


@runtime_checkable
class WorkspaceProvider(Protocol):
    """Contrato de acesso (somente leitura) a um projeto local.

    Implementações devem ser assíncronas (I/O fora do event loop) e traduzir
    falhas para :class:`backend.utils.errors.WorkspaceError`. Nenhuma operação
    pode acessar caminhos fora da raiz configurada.
    """

    @property
    def root(self) -> str | None:
        """Raiz atual (caminho absoluto), ou ``None`` se nenhuma foi definida."""
        ...

    async def set_root(self, path: str) -> str:
        """Define a raiz do projeto (valida que existe e é diretório)."""
        ...

    async def tree(self) -> list[TreeEntry]:
        """Lista arquivos/pastas do projeto (ignorando ruído), até o limite."""
        ...

    async def read_file(self, rel_path: str) -> FileContent:
        """Lê um arquivo de texto do projeto (confinado à raiz, com limite)."""
        ...

    async def search(self, query: str, *, max_hits: int = 100) -> list[SearchHit]:
        """Busca textual simples nos arquivos do projeto."""
        ...
