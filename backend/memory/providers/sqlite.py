"""Adapter de persistência em SQLite (Repository Pattern, ADR-0012).

Usa o ``sqlite3`` da stdlib — sem dependência nova. Como o backend é assíncrono,
toda operação de I/O roda em ``asyncio.to_thread`` para **não bloquear o event
loop**; uma única conexão (``check_same_thread=False``) é serializada por um lock
de thread, o que é suficiente para o volume local de um único usuário.

Timestamps são gravados como ISO 8601 em UTC (texto) e relidos com
``datetime.fromisoformat`` — determinístico e independente de locale.
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.brain.ports import Role
from backend.memory.ports import Conversation, StoredMessage
from backend.utils.errors import StorageError
from backend.utils.logging import get_logger

logger = get_logger(__name__)

#: DDL idempotente aplicada no startup. Sem framework de migração (KISS): volume
#: baixo, um único usuário local. ``ON DELETE CASCADE`` limpa as mensagens junto.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id  TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role             TEXT NOT NULL,
    content          TEXT NOT NULL,
    model            TEXT,
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, id);
"""


def _now() -> datetime:
    """Instante atual em UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


def _parse_ts(raw: str) -> datetime:
    """Relê um timestamp ISO gravado no banco."""
    return datetime.fromisoformat(raw)


class SqliteConversationRepository:
    """``ConversationRepository`` respaldado por um arquivo SQLite local."""

    def __init__(self, db_path: str) -> None:
        self._is_memory = db_path == ":memory:"
        if not self._is_memory:
            path = Path(db_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            db_path = str(path)
        self._lock = threading.Lock()
        try:
            # check_same_thread=False: a conexão é usada por threads do to_thread,
            # sempre sob o lock, então o acesso permanece serializado.
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
        except sqlite3.Error as exc:  # pragma: no cover - falha de disco/permissão
            raise StorageError(f"Falha ao abrir o banco de memória: {exc}") from exc
        logger.info("memory_sqlite_ready", path=db_path)

    # --- API assíncrona (porta) --------------------------------------------

    async def create_conversation(self, title: str) -> Conversation:
        return await asyncio.to_thread(self._create_conversation, title)

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        return await asyncio.to_thread(self._get_conversation, conversation_id)

    async def list_conversations(self, *, limit: int = 50) -> list[Conversation]:
        return await asyncio.to_thread(self._list_conversations, limit)

    async def delete_conversation(self, conversation_id: str) -> bool:
        return await asyncio.to_thread(self._delete_conversation, conversation_id)

    async def add_message(
        self,
        conversation_id: str,
        role: Role,
        content: str,
        *,
        model: str | None = None,
    ) -> StoredMessage:
        return await asyncio.to_thread(
            self._add_message, conversation_id, role, content, model
        )

    async def recent_messages(
        self, conversation_id: str, *, limit: int
    ) -> list[StoredMessage]:
        return await asyncio.to_thread(self._recent_messages, conversation_id, limit)

    async def list_messages(self, conversation_id: str) -> list[StoredMessage]:
        return await asyncio.to_thread(self._list_messages, conversation_id)

    async def close(self) -> None:
        """Fecha a conexão (chamado no shutdown do lifespan)."""
        await asyncio.to_thread(self._close)

    # --- Implementação síncrona (roda em thread, sob lock) -----------------

    def _create_conversation(self, title: str) -> Conversation:
        conv_id = uuid.uuid4().hex
        ts = _now()
        iso = ts.isoformat()
        clean = (title or "").strip() or "Nova conversa"
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO conversations (id, title, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (conv_id, clean, iso, iso),
                )
                self._conn.commit()
            except sqlite3.Error as exc:
                raise StorageError(f"Falha ao criar conversa: {exc}") from exc
        return Conversation(
            id=conv_id, title=clean, created_at=ts, updated_at=ts, message_count=0
        )

    def _get_conversation(self, conversation_id: str) -> Conversation | None:
        with self._lock:
            try:
                row = self._conn.execute(
                    "SELECT c.id, c.title, c.created_at, c.updated_at, "
                    "(SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) "
                    "AS n FROM conversations c WHERE c.id = ?",
                    (conversation_id,),
                ).fetchone()
            except sqlite3.Error as exc:
                raise StorageError(f"Falha ao ler conversa: {exc}") from exc
        return self._row_to_conversation(row) if row is not None else None

    def _list_conversations(self, limit: int) -> list[Conversation]:
        with self._lock:
            try:
                rows = self._conn.execute(
                    "SELECT c.id, c.title, c.created_at, c.updated_at, "
                    "(SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) "
                    "AS n FROM conversations c "
                    "ORDER BY c.updated_at DESC LIMIT ?",
                    (max(1, limit),),
                ).fetchall()
            except sqlite3.Error as exc:
                raise StorageError(f"Falha ao listar conversas: {exc}") from exc
        return [self._row_to_conversation(r) for r in rows]

    def _delete_conversation(self, conversation_id: str) -> bool:
        with self._lock:
            try:
                cur = self._conn.execute(
                    "DELETE FROM conversations WHERE id = ?", (conversation_id,)
                )
                self._conn.commit()
            except sqlite3.Error as exc:
                raise StorageError(f"Falha ao apagar conversa: {exc}") from exc
            return cur.rowcount > 0

    def _add_message(
        self, conversation_id: str, role: Role, content: str, model: str | None
    ) -> StoredMessage:
        ts = _now()
        iso = ts.isoformat()
        with self._lock:
            try:
                exists = self._conn.execute(
                    "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
                ).fetchone()
                if exists is None:
                    raise StorageError(
                        f"Conversa inexistente: {conversation_id!r}."
                    )
                cur = self._conn.execute(
                    "INSERT INTO messages (conversation_id, role, content, model, "
                    "created_at) VALUES (?, ?, ?, ?, ?)",
                    (conversation_id, role, content, model, iso),
                )
                self._conn.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?",
                    (iso, conversation_id),
                )
                self._conn.commit()
                message_id = int(cur.lastrowid)
            except sqlite3.Error as exc:
                raise StorageError(f"Falha ao gravar mensagem: {exc}") from exc
        return StoredMessage(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            created_at=ts,
        )

    def _recent_messages(
        self, conversation_id: str, limit: int
    ) -> list[StoredMessage]:
        if limit <= 0:
            return []
        with self._lock:
            try:
                # Pega as N mais recentes e reordena para ordem cronológica.
                rows = self._conn.execute(
                    "SELECT * FROM (SELECT id, conversation_id, role, content, model, "
                    "created_at FROM messages WHERE conversation_id = ? "
                    "ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
                    (conversation_id, limit),
                ).fetchall()
            except sqlite3.Error as exc:
                raise StorageError(f"Falha ao ler mensagens: {exc}") from exc
        return [self._row_to_message(r) for r in rows]

    def _list_messages(self, conversation_id: str) -> list[StoredMessage]:
        with self._lock:
            try:
                rows = self._conn.execute(
                    "SELECT id, conversation_id, role, content, model, created_at "
                    "FROM messages WHERE conversation_id = ? ORDER BY id ASC",
                    (conversation_id,),
                ).fetchall()
            except sqlite3.Error as exc:
                raise StorageError(f"Falha ao ler mensagens: {exc}") from exc
        return [self._row_to_message(r) for r in rows]

    def _close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- Mapeamento linha -> modelo ----------------------------------------

    @staticmethod
    def _row_to_conversation(row: sqlite3.Row) -> Conversation:
        return Conversation(
            id=row["id"],
            title=row["title"],
            created_at=_parse_ts(row["created_at"]),
            updated_at=_parse_ts(row["updated_at"]),
            message_count=int(row["n"]),
        )

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> StoredMessage:
        return StoredMessage(
            id=int(row["id"]),
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            model=row["model"],
            created_at=_parse_ts(row["created_at"]),
        )
