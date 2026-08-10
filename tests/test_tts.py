"""Testes da camada de TTS e da integração de voz no fluxo de conversa."""

from __future__ import annotations

import pytest

from backend.brain.events import AudioReady
from backend.config.settings import Settings
from backend.tts.factory import create_tts_provider
from backend.tts.providers.piper import PiperTTSProvider
from backend.tts.text import to_speech_text
from backend.utils.errors import ProviderConfigError, TTSError, TTSUnavailableError
from tests.conftest import (
    FakeLLMProvider,
    FakeTTSProvider,
    build_conversation_service,
)


def test_to_speech_text_strips_symbols_and_markdown() -> None:
    """Markdown, símbolos, URLs e citações não devem sobrar para a fala."""
    raw = (
        "**Ollama** é uma ferramenta *local* (Fonte: [1] Guia). "
        "Veja [o site](https://ollama.com) e https://x.com/y — item.\n"
        "- primeiro\n- segundo #tag"
    )
    spoken = to_speech_text(raw)
    for symbol in ("*", "#", "[", "]", "(", ")", "/", "http", "Fonte"):
        assert symbol not in spoken
    assert "Ollama" in spoken and "local" in spoken
    assert "o site" in spoken  # rótulo do link preservado


def test_to_speech_text_drops_fenced_code_blocks() -> None:
    """Blocos de código não devem ser lidos linha a linha; viram uma pista curta."""
    raw = (
        "Aqui está um exemplo:\n"
        "```html\n<!DOCTYPE html>\n<body><h1>Loja</h1></body>\n```\n"
        "E o estilo:\n```css\nbody { margin: 0; }\n```\n"
        "Adapte às suas necessidades."
    )
    spoken = to_speech_text(raw)
    for leaked in ("DOCTYPE", "body", "margin", "<", "{"):
        assert leaked not in spoken
    assert "Aqui está um exemplo" in spoken
    assert "Adapte às suas necessidades" in spoken
    assert "Código exibido na tela" in spoken


def test_to_speech_text_drops_unterminated_code_block() -> None:
    """Bloco de código não fechado (modelo cortado) não deve vazar na fala."""
    raw = "Segue o código:\n```python\nprint('oi')\nfor i in range(10):"
    spoken = to_speech_text(raw)
    assert "print" not in spoken and "range" not in spoken
    assert "Segue o código" in spoken


def test_to_speech_text_keeps_sentence_punctuation() -> None:
    """Pontuação de frase é preservada; não sobra espaço antes dela."""
    assert to_speech_text("Olá, mundo! Tudo bem?") == "Olá, mundo! Tudo bem?"


def test_factory_creates_piper() -> None:
    """A fábrica deve devolver o adapter Piper por padrão."""
    provider = create_tts_provider(Settings(_env_file=None))
    assert isinstance(provider, PiperTTSProvider)


def test_factory_rejects_unknown_provider() -> None:
    """Provedor de TTS desconhecido deve falhar na fábrica."""
    with pytest.raises(ProviderConfigError):
        create_tts_provider(Settings(_env_file=None, tts_provider="espeak"))


async def test_piper_synthesize_empty_text_raises() -> None:
    """Texto vazio não deve chamar o Piper."""
    provider = PiperTTSProvider(binary="piper", voice="voz.onnx")
    with pytest.raises(TTSError):
        await provider.synthesize("   ")


async def test_piper_missing_binary_is_unavailable() -> None:
    """Binário inexistente deve virar TTSUnavailableError (exceção do domínio)."""
    provider = PiperTTSProvider(
        binary="piper-inexistente-xyz", voice=__file__  # arquivo existe p/ passar do voice check
    )
    with pytest.raises(TTSUnavailableError):
        await provider.synthesize("olá")


async def test_conversation_emits_audio_when_tts_enabled() -> None:
    """Com TTS ativo, o turno deve emitir um AudioReady após a resposta."""
    tts = FakeTTSProvider()
    service = build_conversation_service(
        llm=FakeLLMProvider(tokens=["oi"]), tts=tts, tts_enabled=True
    )
    events = [e async for e in service.run("pergunta")]
    audios = [e for e in events if isinstance(e, AudioReady)]
    assert len(audios) == 1
    assert audios[0].mime == "audio/wav"
    assert tts.calls == ["oi"]  # sintetizou a resposta acumulada


async def test_conversation_no_audio_when_tts_disabled() -> None:
    """Com TTS desativado, nenhum AudioReady é emitido."""
    tts = FakeTTSProvider()
    service = build_conversation_service(tts=tts, tts_enabled=False)
    events = [e async for e in service.run("pergunta")]
    assert not any(isinstance(e, AudioReady) for e in events)
    assert tts.calls == []


async def test_conversation_degrades_when_tts_fails() -> None:
    """Falha de TTS não interrompe o turno; apenas omite o áudio."""
    service = build_conversation_service(
        llm=FakeLLMProvider(tokens=["ok"]), tts=FakeTTSProvider(fail=True), tts_enabled=True
    )
    events = [e async for e in service.run("pergunta")]
    assert not any(isinstance(e, AudioReady) for e in events)
    # o turno ainda conclui normalmente
    from backend.brain.events import TurnCompleted

    assert any(isinstance(e, TurnCompleted) for e in events)
