"""Camada de memória de longo prazo (persistência de conversas).

Ports & Adapters + Repository Pattern (ADR-0012): o domínio depende da porta
:class:`~backend.memory.ports.ConversationRepository`, nunca de um banco
concreto. O adapter atual é SQLite (:mod:`backend.memory.providers.sqlite`).
"""
