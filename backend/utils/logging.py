"""Configuração de logging estruturado via structlog.

Em desenvolvimento emite console colorido e legível; em produção emite JSON,
adequado para coleta por ferramentas de observabilidade. A escolha é feita por
configuração (``FRIDAY_LOG_JSON``), sem alterar o código que loga.
"""

from __future__ import annotations

import logging
import sys

import structlog

_configured = False


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """Configura o logging global da aplicação (idempotente).

    Args:
        level: Nível mínimo de log (ex.: ``"INFO"``, ``"DEBUG"``).
        json_logs: Se True, saída em JSON; caso contrário, console legível.
    """
    global _configured
    if _configured:
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=numeric_level,
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Retorna um logger estruturado, opcionalmente nomeado."""
    return structlog.get_logger(name)
