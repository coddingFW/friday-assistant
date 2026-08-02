# PHASE_REPORT_04 — Voz / TTS (Fase 4)

## Objetivos
Integrar síntese de voz (Piper): converter a resposta em áudio e reproduzi-la no
cliente, mantendo o backend agnóstico de hardware de áudio.

## Arquivos criados
- `backend/tts/ports.py` — `TTSProvider` (porta) + `SpeechAudio`.
- `backend/tts/providers/piper.py` — adapter Piper (subprocesso, resolução robusta
  do binário: arquivo → venv → PATH).
- `backend/tts/factory.py` — seleção do provedor (Strategy).
- `backend/tts/__init__.py`.
- `tests/test_tts.py`.

## Arquivos modificados
- `config/settings.py` — `tts_enabled`, `tts_provider`, `piper_binary`, `piper_voice`, `tts_timeout`.
- `utils/errors.py` — `TTSError`, `TTSUnavailableError`.
- `brain/events.py` — evento `AudioReady`.
- `brain/conversation.py` — acumula a resposta e sintetiza ao final (degradação graciosa).
- `api/websocket/{protocol,chat.py}` — evento `audio` (WAV base64).
- `main.py` — cria o provedor TTS e injeta no `ConversationService`.
- Frontend: `types.ts`, `hooks/useChat.ts` (autoplay), `components/MessageList.tsx`
  (botão "Ouvir"), `styles.css`.
- `.env.example`, `requirements.txt`.

## Dependências
Adicionada: **`piper-tts`** (traz `onnxruntime`, `numpy`). Modelo de voz PT-BR
`pt_BR-faber-medium.onnx` (~61 MB) baixado à parte em `models/` (não versionado).

## Decisão de arquitetura
**ADR-0007**: o Host sintetiza (Piper) e o cliente reproduz; o áudio vai no evento
WebSocket `audio` (base64). Consistente com a topologia Host+Cliente (essencial
para o mobile: o som sai no dispositivo do usuário, não no Host).

## Como validado
- **45 testes verdes** (37 → 45): fábrica, adapter (texto vazio, binário ausente),
  integração (áudio emitido com TTS on, ausente com off, degradação em falha) e
  WebSocket (evento `audio` presente). TypeScript do frontend compila limpo.
- **Síntese real** validada: Piper gerou WAV válido (assinatura `RIFF`, ~115–158 KB).
- Backend reiniciado com `tts_enabled=True` — pronto para ouvir no app.

## Checklist
- [x] Camada TTS (porta + adapter Piper + fábrica, Strategy)
- [x] Integração no fluxo de conversa (evento `AudioReady`)
- [x] Protocolo WS com evento `audio` (base64)
- [x] Reprodução no cliente (autoplay + botão "Ouvir")
- [x] Degradação graciosa (TTS off/erro não quebra o turno)
- [x] Síntese real validada + testes verdes

## Problemas encontrados e corrigidos
- **Caminho do binário no Windows**: caminho relativo/com barras quebra o
  `CreateProcess`. Adapter agora resolve o binário (arquivo → venv → PATH), então
  o default `FRIDAY_PIPER_BINARY=piper` já funciona com o `piper-tts` do venv.
- **Símbolos lidos em voz alta**: a resposta do LLM traz markdown/URLs/citações que
  o Piper soletrava. Adicionado `backend/tts/text.py` (`to_speech_text`) que limpa
  o texto **só para a fala** (o exibido mantém a formatação).
- **Acento agudo virava "til"** (mojibake): o Piper (Python) lia o stdin em cp1252,
  então UTF-8 "é" (C3 A9) virava "Ã©" e o "Ã" (A-til) era falado como "til".
  Corrigido executando o Piper com `PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8`.
  Confirmado por teste auditivo do usuário (com fix = correto).

## Limitações / Melhorias futuras
- Síntese da resposta **completa** ao final (não streaming por sentença) — menor
  complexidade; streaming + visemas entram na Fase 5 (avatar).
- Sem seleção de voz/velocidade na UI (configurável por env).
- Voz PT-BR precisa ser baixada por máquina (ver SETUP).

## Pendências
- Validação auditiva pelo usuário (ouvir a resposta no app).
