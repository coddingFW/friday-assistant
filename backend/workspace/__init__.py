"""Camada de workspace — acesso de LEITURA a um projeto local (Fase 10).

Ports & Adapters (ADR-0013): o domínio depende da porta
:class:`~backend.workspace.ports.WorkspaceProvider`; o adapter atual lê o sistema
de arquivos local (:mod:`backend.workspace.providers.local_fs`), sempre confinado
à raiz escolhida pelo usuário. Nesta fatia a Friday **lê e ensina** — não escreve.
"""
