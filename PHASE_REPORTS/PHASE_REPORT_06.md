# PHASE_REPORT_06 — STT: voz de entrada (Fase 6)

## Objetivos
Permitir falar com a Friday: capturar o microfone, transcrever localmente e levar
a transcrição à conversa — concretizando o primeiro sensor real da camada de
percepção. Escopo: **push-to-talk** (escuta contínua + wake word é a Fase 7).

## Arquivos criados
- `backend/stt/ports.py` — `STTProvider` (Strategy) + `Transcript`.
- `backend/stt/providers/whisper.py` — adapter faster-whisper/CTranslate2: inferência
  em worker thread, carga preguiçosa do modelo, reamostragem linear p/ 16 kHz.
- `backend/stt/factory.py` — seleção do provedor por config.
- `backend/perception/sensors/microphone.py` — `MicrophoneSensor` (1º `StreamingSensor`)
  + `EnergyEndpointer` (VAD por RMS, numpy).
- `ADR/ADR-0009.md`; testes `test_stt.py`, `test_microphone_sensor.py`, `test_ws_listen.py`.

## Arquivos modificados
- `config/settings.py` — bloco STT (`stt_enabled`, `whisper_*`) e microfone (`mic_*`).
- `main.py` — cria o `STTProvider` e registra o `MicrophoneSensor` quando `stt_enabled`.
- `api/websocket/protocol.py` — `listen_start`/`listen_stop`, `transcript`, status `listening`.
- `api/websocket/chat.py` — roteamento por tipo + fluxo de escuta com lock de envio.
- `api/dependencies.py`, `utils/errors.py` — `get_stt_provider`, `STTError`/`AudioCaptureError`.
- `requirements.txt` — `faster-whisper`, `sounddevice`, `numpy`.
- **Frontend:** `types.ts`, `services/chatSocket.ts`, `hooks/useChat.ts`,
  `components/Composer.tsx` (mic + toggle auto-enviar), `StatusIndicator.tsx`,
  `Avatar3D.tsx`, `App.tsx`, `styles.css`.

## Decisões de arquitetura
**ADR-0009**: captura no Host como `MicrophoneSensor`; STT Whisper via Strategy em
thread; VAD por energia (webrtcvad descartado por falta de wheel no Python 3.14);
transcrição via `/ws/chat`; o cliente decide auto-enviar (preferência do usuário).

## Como validado
- **Backend:** suíte com **63 testes verdes** (12 novos de STT/microfone/WS).
  O endpointer, o `stream()` do sensor e o fluxo `listen_*`→`transcript` são
  cobertos com fakes (sem microfone nem modelo reais).
- **Stack:** `faster-whisper` (ctranslate2 4.8.1) e `sounddevice` importam no
  Python 3.14; 11 dispositivos de entrada detectados.
- **Frontend:** `tsc --noEmit` limpo (exit 0).

## Limitações / pendências
- **Validação real pendente (usuário):** falar e ver a transcrição — o 1º uso baixa
  o modelo Whisper do HuggingFace (~500 MB p/ `small`); depois roda offline.
- `perceive()` é consumido por uma conexão por vez (usuário único local).
- Endpointing por energia é simples; ruído alto pode exigir ajustar `mic_energy_threshold`.
- Sem transcrição parcial ao vivo (só final por fala) — evolução futura.

## Checklist
- [x] `MicrophoneSensor` (1º StreamingSensor) + VAD por energia
- [x] `STTProvider` Whisper (thread, carga preguiçosa) via Strategy
- [x] Fluxo `listen_start`/`listen_stop`/`transcript` no WebSocket
- [x] Botão de microfone + toggle de auto-enviar (persistido) no frontend
- [x] Testes verdes (backend) e TS limpo (frontend)
- [ ] Validação falada real (usuário) + ajuste fino do limiar
