"""Portas (interfaces) da camada de workspace — Ports & Adapters.

O domínio depende apenas destas abstrações. O adapter concreto (sistema de
arquivos local) implementa :class:`WorkspaceProvider`. Toda operação é confinada
à raiz escolhida pelo usuário; sair dela é erro, nunca silêncio. A escrita é
sempre iniciada pelo usuário (nunca pela IA por conta própria) e guarda um backup
do conteúdo anterior antes de sobrescrever.
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


@dataclass(frozen=True, slots=True)
class WriteResult:
    """Resultado de uma escrita de arquivo do projeto."""

    path: str  # relativo à raiz
    created: bool  # True se o arquivo não existia (criado agora)
    bytes_written: int
    backup_path: str | None  # backup do conteúdo anterior (None quando criado)


@runtime_checkable
class WorkspaceProvider(Protocol):
    """Contrato de acesso a um projeto local (leitura + escrita confinada).

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

    async def write_file(self, rel_path: str, text: str) -> WriteResult:
        """Escreve um arquivo de texto do projeto (confinado à raiz).

        Cria ou sobrescreve o arquivo; ao sobrescrever, guarda antes um backup
        do conteúdo anterior. Recusa: caminho fora da raiz, dentro de diretório
        ignorado, sobre um diretório, tipo não-texto, ou se a escrita estiver
        desativada por configuração.
        """
        ...
