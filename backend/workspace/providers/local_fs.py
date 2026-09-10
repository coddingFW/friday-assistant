"""Adapter de workspace sobre o sistema de arquivos local (leitura) — ADR-0013.

Confina TODO acesso à raiz escolhida pelo usuário: caminhos são resolvidos
(``Path.resolve``, seguindo symlinks) e recusados se saírem da raiz. I/O
bloqueante roda em ``asyncio.to_thread`` para não travar o event loop.

Somente leitura nesta fatia: a Friday lê e ensina, não escreve.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from backend.workspace.ports import FileContent, SearchHit, TreeEntry
from backend.utils.errors import WorkspaceError
from backend.utils.logging import get_logger

logger = get_logger(__name__)

#: Sufixos tratados como texto legível. Fora disto, o arquivo é pulado na busca
#: e recusado na leitura (evita despejar binário no prompt do LLM).
_TEXT_SUFFIXES = frozenset({
    ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".txt", ".html", ".css",
    ".scss", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".env", ".sh", ".ps1",
    ".bat", ".sql", ".rs", ".go", ".java", ".kt", ".c", ".h", ".cpp", ".hpp",
    ".cs", ".rb", ".php", ".vue", ".svelte", ".xml", ".gradle", ".dockerfile",
    ".gitignore", ".gitattributes", ".editorconfig", ".lua", ".r", ".dart",
})


def _looks_binary(sample: bytes) -> bool:
    """Heurística: presença de byte nulo indica binário."""
    return b"\x00" in sample


class LocalFsWorkspace:
    """``WorkspaceProvider`` de leitura sobre uma pasta local escolhida."""

    def __init__(
        self,
        *,
        ignore_dirs: list[str],
        max_file_kb: int,
        max_tree_entries: int,
    ) -> None:
        self._ignore = {d.lower() for d in ignore_dirs}
        self._max_file_bytes = max_file_kb * 1024
        self._max_entries = max_tree_entries
        self._root: Path | None = None

    @property
    def root(self) -> str | None:
        return str(self._root) if self._root is not None else None

    async def set_root(self, path: str) -> str:
        return await asyncio.to_thread(self._set_root, path)

    async def tree(self) -> list[TreeEntry]:
        return await asyncio.to_thread(self._tree)

    async def read_file(self, rel_path: str) -> FileContent:
        return await asyncio.to_thread(self._read_file, rel_path)

    async def search(self, query: str, *, max_hits: int = 100) -> list[SearchHit]:
        return await asyncio.to_thread(self._search, query, max_hits)

    # --- Implementação síncrona (roda em thread) ---------------------------

    def _set_root(self, path: str) -> str:
        if not path or not path.strip():
            raise WorkspaceError("Informe o caminho da pasta do projeto.")
        try:
            resolved = Path(path.strip()).expanduser().resolve()
        except (OSError, RuntimeError) as exc:
            raise WorkspaceError(f"Caminho inválido: {exc}") from exc
        if not resolved.exists():
            raise WorkspaceError(f"A pasta não existe: {resolved}")
        if not resolved.is_dir():
            raise WorkspaceError(f"O caminho não é uma pasta: {resolved}")
        self._root = resolved
        logger.info("workspace_root_set", path=str(resolved))
        return str(resolved)

    def _require_root(self) -> Path:
        if self._root is None:
            raise WorkspaceError("Nenhuma pasta de projeto definida.")
        return self._root

    def _safe_path(self, rel_path: str) -> Path:
        """Resolve ``rel_path`` sob a raiz, recusando qualquer escape."""
        root = self._require_root()
        candidate = (root / rel_path).resolve()
        if candidate != root and root not in candidate.parents:
            raise WorkspaceError(f"Caminho fora do projeto: {rel_path!r}.")
        return candidate

    def _is_ignored(self, parts: tuple[str, ...]) -> bool:
        return any(p.lower() in self._ignore for p in parts)

    def _tree(self) -> list[TreeEntry]:
        root = self._require_root()
        entries: list[TreeEntry] = []
        for dirpath, dirnames, filenames in os.walk(root):
            # Poda diretórios ignorados in-place (não desce neles).
            dirnames[:] = sorted(d for d in dirnames if d.lower() not in self._ignore)
            rel_dir = Path(dirpath).relative_to(root)
            for d in dirnames:
                rel = (rel_dir / d).as_posix()
                entries.append(TreeEntry(path=rel, name=d, is_dir=True))
                if len(entries) >= self._max_entries:
                    return entries
            for f in sorted(filenames):
                rel = (rel_dir / f).as_posix()
                try:
                    size = (root / rel).stat().st_size
                except OSError:
                    size = 0
                entries.append(TreeEntry(path=rel, name=f, is_dir=False, size=size))
                if len(entries) >= self._max_entries:
                    return entries
        return entries

    def _read_file(self, rel_path: str) -> FileContent:
        path = self._safe_path(rel_path)
        if not path.is_file():
            raise WorkspaceError(f"Arquivo não encontrado: {rel_path}")
        size = path.stat().st_size
        try:
            with path.open("rb") as fh:
                raw = fh.read(self._max_file_bytes + 1)
        except OSError as exc:
            raise WorkspaceError(f"Falha ao ler {rel_path}: {exc}") from exc
        if _looks_binary(raw[:4096]):
            raise WorkspaceError(f"Arquivo binário não é legível como texto: {rel_path}")
        truncated = len(raw) > self._max_file_bytes
        text = raw[: self._max_file_bytes].decode("utf-8", errors="replace")
        return FileContent(
            path=Path(rel_path).as_posix(), text=text, truncated=truncated, size=size
        )

    def _search(self, query: str, max_hits: int) -> list[SearchHit]:
        root = self._require_root()
        needle = query.lower()
        if not needle.strip():
            return []
        hits: list[SearchHit] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d.lower() not in self._ignore]
            for f in filenames:
                if Path(f).suffix.lower() not in _TEXT_SUFFIXES:
                    continue
                fpath = Path(dirpath) / f
                try:
                    with fpath.open("r", encoding="utf-8", errors="replace") as fh:
                        for i, line in enumerate(fh, start=1):
                            if needle in line.lower():
                                rel = fpath.relative_to(root).as_posix()
                                hits.append(
                                    SearchHit(path=rel, line=i, text=line.strip()[:200])
                                )
                                if len(hits) >= max_hits:
                                    return hits
                except OSError:
                    continue
        return hits
