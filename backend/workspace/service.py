"""Serviço de workspace — fachada de domínio sobre o provedor de leitura.

É o ponto que a API (REST e WebSocket) consome. Além de repassar as operações de
leitura, monta o **bloco de contexto de código**: concatena os arquivos pedidos,
cada um com um cabeçalho, respeitando um orçamento de caracteres para não estourar
o prompt do LLM local.
"""

from __future__ import annotations

from collections.abc import Sequence

from backend.workspace.ports import (
    FileContent,
    SearchHit,
    TreeEntry,
    WorkspaceProvider,
)
from backend.utils.errors import WorkspaceError
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class WorkspaceService:
    """Casos de uso do projeto local, sobre a porta do provedor (só leitura)."""

    def __init__(self, provider: WorkspaceProvider, *, context_char_budget: int) -> None:
        self._provider = provider
        self._budget = context_char_budget

    @property
    def root(self) -> str | None:
        return self._provider.root

    async def set_root(self, path: str) -> str:
        return await self._provider.set_root(path)

    async def tree(self) -> list[TreeEntry]:
        return await self._provider.tree()

    async def read_file(self, rel_path: str) -> FileContent:
        return await self._provider.read_file(rel_path)

    async def search(self, query: str, *, max_hits: int = 100) -> list[SearchHit]:
        return await self._provider.search(query, max_hits=max_hits)

    async def build_context_blocks(self, paths: Sequence[str]) -> list[str]:
        """Monta blocos de contexto (system) a partir dos arquivos pedidos.

        Cada bloco é o conteúdo de um arquivo com cabeçalho identificando o
        caminho. Respeita o orçamento total de caracteres: ao estourar, para de
        incluir arquivos e anexa um aviso. Arquivos ilegíveis (binário/erro) são
        pulados com uma nota, sem derrubar o turno.
        """
        blocks: list[str] = []
        used = 0
        incluidos = 0
        for rel in paths:
            if used >= self._budget:
                blocks.append(
                    "[Contexto truncado: orçamento de caracteres atingido; "
                    "arquivos restantes não foram incluídos.]"
                )
                break
            try:
                fc = await self._provider.read_file(rel)
            except WorkspaceError as exc:
                blocks.append(f"[Arquivo não incluído: {rel} — {exc}]")
                continue
            disponivel = self._budget - used
            corpo = fc.text
            nota = " (truncado)" if fc.truncated else ""
            if len(corpo) > disponivel:
                corpo = corpo[:disponivel]
                nota = " (truncado pelo orçamento)"
            bloco = f"Arquivo do projeto: {fc.path}{nota}\n```\n{corpo}\n```"
            blocks.append(bloco)
            used += len(corpo)
            incluidos += 1
        logger.info("workspace_context_built", files=incluidos, chars=used)
        return blocks
