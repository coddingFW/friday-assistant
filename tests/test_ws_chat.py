"""Testes do WebSocket de chat (streaming em tempo real, com RAG)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import create_app
from tests.conftest import (
    FakeLLMProvider,
    FakeSearchProvider,
    FakeTTSProvider,
    build_conversation_service,
)


def _app_with_service(service) -> object:
    app = create_app()
    app.state.conversation_service = service
    return app


def test_ws_full_flow_with_rag() -> None:
    """Turno com RAG: thinking -> searching -> sources -> responding -> tokens -> done."""
    service = build_conversation_service(llm=FakeLLMProvider(tokens=["a", "b"]))
    app = _app_with_service(service)

    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "user_message", "content": "clima hoje?"})

        assert ws.receive_json() == {"type": "status", "state": "thinking"}
        assert ws.receive_json() == {"type": "status", "state": "searching"}
        sources = ws.receive_json()
        assert sources["type"] == "sources"
        assert sources["sources"][0]["url"] == "https://ex.com"
        assert ws.receive_json() == {"type": "status", "state": "responding"}
        assert [ws.receive_json()["content"] for _ in range(2)] == ["a", "b"]
        assert ws.receive_json() == {"type": "done"}
        assert ws.receive_json() == {"type": "status", "state": "idle"}


def test_ws_degrades_when_search_fails() -> None:
    """Se a busca falhar, o turno segue sem 'sources' e ainda responde."""
    service = build_conversation_service(
        llm=FakeLLMProvider(tokens=["ok"]), search=FakeSearchProvider(fail=True)
    )
    app = _app_with_service(service)

    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "user_message", "content": "oi"})
        assert ws.receive_json() == {"type": "status", "state": "thinking"}
        assert ws.receive_json() == {"type": "status", "state": "searching"}
        # sem evento de 'sources' — vai direto para responding
        assert ws.receive_json() == {"type": "status", "state": "responding"}
        assert ws.receive_json() == {"type": "token", "content": "ok"}
        assert ws.receive_json() == {"type": "done"}
        assert ws.receive_json() == {"type": "status", "state": "idle"}


def test_ws_emits_audio_event_when_tts_on() -> None:
    """Com TTS ativo, o cliente deve receber um evento 'audio' (base64) antes do done."""
    service = build_conversation_service(
        llm=FakeLLMProvider(tokens=["oi"]), tts=FakeTTSProvider(), tts_enabled=True
    )
    app = _app_with_service(service)
    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "user_message", "content": "oi"})
        events = []
        while True:
            ev = ws.receive_json()
            events.append(ev)
            if ev["type"] == "done":
                break
        audio = [e for e in events if e["type"] == "audio"]
        assert len(audio) == 1
        assert audio[0]["mime"] == "audio/wav"
        assert isinstance(audio[0]["data"], str) and audio[0]["data"]


def _drain_turn(ws) -> None:
    """Consome os eventos de um turno até o 'done' (inclusive)."""
    while ws.receive_json()["type"] != "done":
        pass
    ws.receive_json()  # status idle final


def test_ws_remembers_previous_turn_in_same_connection() -> None:
    """O 2º turno deve receber o par (user, assistant) do 1º turno como contexto."""
    llm = FakeLLMProvider(tokens=["Viktor", " Frankl"])
    service = build_conversation_service(llm=llm, rag_enabled=False)
    app = _app_with_service(service)

    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "user_message", "content": "quem citou o sentido da vida?"})
        _drain_turn(ws)
        ws.send_json({"type": "user_message", "content": "qual o nome dele?"})
        _drain_turn(ws)

    # O 2º turno viu a pergunta e a resposta do 1º (memória de curto prazo).
    second_turn_messages = llm.calls[-1]
    contents = [m.content for m in second_turn_messages]
    assert "quem citou o sentido da vida?" in contents
    assert "Viktor Frankl" in contents  # resposta acumulada do 1º turno
    assert second_turn_messages[-1].content == "qual o nome dele?"


def test_ws_rejects_invalid_message() -> None:
    """Mensagem sem 'content' deve retornar um evento de erro, sem cair."""
    app = _app_with_service(build_conversation_service())
    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "user_message"})
        assert ws.receive_json()["type"] == "error"
