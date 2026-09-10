"""Fábrica do provedor de workspace — estratégia por configuração."""

from __future__ import annotations

from backend.config.settings import Settings
from backend.workspace.ports import WorkspaceProvider
from backend.workspace.providers.local_fs import LocalFsWorkspace


def create_workspace_provider(settings: Settings) -> WorkspaceProvider:
    """Cria o provedor de workspace. Hoje há um único backend (sistema de
    arquivos local); a fábrica mantém a troca como decisão de configuração."""
    return LocalFsWorkspace(
        ignore_dirs=settings.workspace_ignore_dirs,
        max_file_kb=settings.workspace_max_file_kb,
        max_tree_entries=settings.workspace_max_tree_entries,
    )
