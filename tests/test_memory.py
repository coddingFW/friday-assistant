"""Testes da Fase 9 (memória de longo prazo): repositório SQLite, serviço,
REST de conversas e integração com o WebSocket (criar/retomar/persistir)."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from backend.brain.ports import ChatMessage
from backend.main import create_app
from backend.memory.providers.sqlite import SqliteConversationRepository
from backend.memory.service import MemoryService
from tests.conftest import FakeLLMProvider, build_conversation_service


def _repo() -> SqliteConversationRepository:
    """Repositório em memória, isolado por teste."""
    return SqliteConversationRepository(":memory:")


# --- Repositório SQLite -----------------------------------------------------


async def test_repo_create_and_get_roundtrip() -> None:
    """Criar uma conversa e relê-la preserva título e timestamps."""
    repo = _repo()
    conv = await repo.create_conversation("Primeira")
    again = await repo.get_conversation(conv.id)
    assert again is not None
    assert again.id == conv.id
    assert again.title == "Primeira"
    assert again.message_count == 0
    assert await repo.get_conversation("inexistente") is None


async def test_repo_recent_messages_windows_and_orders() -> None:
    """recent_messages devolve as N últimas em ordem cronológica."""
    repo = _repo()
    conv = await repo.create_conversation("c")
    for i in range(5):
        await repo.add_message(conv.id, "user", f"m{i}")
    janela = await repo.recent_messages(conv.id, limit=3)
    assert [m.content for m in janela] == ["m2", "m3", "m4"]
    # message_count reflete o total, não a janela.
    reread = await repo.get_conversation(conv.id)
    assert reread is not None and reread.message_count == 5


async def test_repo_delete_cascades_and_reports_missing() -> None:
    """Apagar remove as mensagens junto; apagar inexistente devolve False."""
    repo = _repo()
    conv = await repo.create_conversation("c")
    await repo.add_message(conv.id, "user", "oi")
    assert await repo.delete_conversation(conv.id) is True
    assert await repo.get_conversation(conv.id) is None
    assert await repo.list_messages(conv.id) == []
    assert await repo.delete_conversation(conv.id) is False


# --- Serviço de memória -----------------------------------------------------


async def test_service_derives_title_from_first_message() -> None:
    """O título de uma conversa nova sai da 1ª linha da primeira mensagem."""
    memory = MemoryService(_repo())
    conv = await memory.start_conversation("  Como faço um bolo?\ndetalhes...  ")
    assert conv.title == "Como faço um bolo?"
    longa = await memory.start_conversation("x" * 100)
    assert longa.title.endswith("…") and len(longa.title) <= 60


async def test_service_record_turn_and_history_window() -> None:
    """record_turn persiste o par; history_window devolve ChatMessage cronológico."""
    memory = MemoryService(_repo())
    conv = await memory.start_conversation("pergunta")
    await memory.record_turn(conv.id, "pergunta", "resposta", model="fake")
    window = await memory.history_window(conv.id, limit=12)
    assert window == [
        ChatMessage(role="user", content="pergunta"),
        ChatMessage(role="assistant", content="resposta"),
    ]


# --- REST de conversas ------------------------------------------------------


def _app_with_memory(memory: MemoryService, service=None):
    app = create_app()
    app.state.memory_service = memory
    if service is not None:
        app.state.conversation_service = service
    return app


def test_rest_list_get_and_delete_conversation() -> None:
    """Fluxo REST: listar, ler com mensagens e apagar uma conversa."""

    memory = MemoryService(_repo())

    async def seed():
        conv = await memory.start_conversation("Assunto")
        await memory.record_turn(conv.id, "oi", "olá")
        return conv.id

    conv_id = asyncio.run(seed())
    client = TestClient(_app_with_memory(memory))

    listing = client.get("/api/conversations")
    assert listing.status_code == 200
    assert listing.json()[0]["id"] == conv_id
    assert listing.json()[0]["message_count"] == 2

    detail = client.get(f"/api/conversations/{conv_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"] == "Assunto"
    assert [m["content"] for m in body["messages"]] == ["oi", "olá"]

    assert client.delete(f"/api/conversations/{conv_id}").status_code == 204
    assert client.get(f"/api/conversations/{conv_id}").status_code == 404


def test_rest_get_missing_conversation_is_404() -> None:
    """Ler uma conversa inexistente devolve 404."""
    client = TestClient(_app_with_memory(MemoryService(_repo())))
    assert client.get("/api/conversations/nada").status_code == 404


# --- Integração com o WebSocket ---------------------------------------------


def _drain_turn(ws) -> list[dict]:
    """Consome os eventos até o 'done' (inclusive) e devolve todos eles."""
    events = []
    while True:
        ev = ws.receive_json()
        events.append(ev)
        if ev["type"] == "done":
            break
    ws.receive_json()  # status idle final
    return events


def test_ws_creates_and_persists_conversation() -> None:
    """1ª mensagem cria uma conversa (evento 'conversation') e persiste o turno."""

    memory = MemoryService(_repo())
    service = build_conversation_service(
        llm=FakeLLMProvider(tokens=["oi"]), rag_enabled=False
    )
    app = _app_with_memory(memory, service)

    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "user_message", "content": "olá mundo"})
        first = ws.receive_json()
        assert first["type"] == "conversation"
        assert first["title"] == "olá mundo"
        conv_id = first["id"]
        _drain_turn(ws)

    async def check():
        msgs = await memory.list_messages(conv_id)
        return [(m.role, m.content) for m in msgs]

    assert asyncio.run(check()) == [("user", "olá mundo"), ("assistant", "oi")]


def test_ws_resumes_conversation_and_seeds_history() -> None:
    """Retomar uma conversa por id semeia o histórico anterior como contexto."""

    memory = MemoryService(_repo())

    async def seed():
        conv = await memory.start_conversation("anterior")
        await memory.record_turn(conv.id, "quem foi Ada Lovelace?", "uma pioneira")
        return conv.id

    conv_id = asyncio.run(seed())
    llm = FakeLLMProvider(tokens=["sim"])
    service = build_conversation_service(llm=llm, rag_enabled=False)
    app = _app_with_memory(memory, service)

    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json(
            {"type": "user_message", "content": "e o pai dela?", "conversation_id": conv_id}
        )
        first = ws.receive_json()
        assert first["type"] == "conversation" and first["id"] == conv_id
        _drain_turn(ws)

    # O turno viu o par anterior (semeado do banco) como histórico.
    contents = [m.content for m in llm.calls[-1]]
    assert "quem foi Ada Lovelace?" in contents
    assert "uma pioneira" in contents
    assert llm.calls[-1][-1].content == "e o pai dela?"
