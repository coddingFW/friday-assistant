# PHASE_REPORT_08 — Visão / Multimodalidade (MVP)

## Objetivos
Dar visão à Friday: enviar uma imagem (upload) ou a tela do Host e perguntar
sobre ela, respondida por um modelo multimodal local. Escopo do MVP: **imagem +
captura de tela + LLM de visão**. (Webcam e OCR dedicado ficam para depois.)

## Arquivos criados
- `backend/perception/sensors/screen.py` — `ScreenCaptureSensor` (OnDemand, mss).
- `backend/api/rest/vision.py` — `GET /api/vision/screen` (base64).
- `ADR/ADR-0011.md`; `tests/test_vision.py`.
- `frontend/src/services/api.ts` (`captureScreen`) — método REST.

## Arquivos modificados
- `config/settings.py` — `vision_enabled`, `vision_model` (default `llava`).
- `brain/conversation.py` + `rag/service.py` — imagens anexadas à mensagem, uso do
  modelo de visão quando há imagem, e **pular RAG** nesse caso.
- `api/websocket/protocol.py` + `chat.py` — `UserMessage.images`; repasse ao turno.
- `perception/manager.py` — `snapshot()` (captura on-demand sem enfileirar).
- `main.py` — registra o `ScreenCaptureSensor` (se `vision_enabled`).
- **Frontend:** `types.ts`, `services/chatSocket.ts`, `hooks/useChat.ts`
  (imagem pendente + envio), `components/Composer.tsx` (📎 anexar, 🖥️ tela,
  preview), `MessageList.tsx` (exibe a imagem), `styles.css`.
- `requirements.txt` — `mss`, `Pillow`. `PROJECT_MANIFEST.md` — Fase 8.

## Decisões de arquitetura
**ADR-0011**: imagem → `ChatMessage.images` → Ollama (modelo de visão); captura de
tela como OnDemandSensor; RAG pulado em turnos com imagem; 100% local.

## Como validado
- **Backend:** suíte com **71 testes verdes** (5 novos: imagem usa o modelo de
  visão e pula RAG; sensor de tela com grabber injetado; `snapshot` sem enfileirar;
  endpoint REST devolve base64). `mss`/`Pillow` instalam no Python 3.14.
- **Frontend:** `tsc --noEmit` limpo; build de produção ok.

## Limitações / pendências
- **Pré-requisito do usuário:** instalar um modelo de visão — `ollama pull llava`
  (senão a resposta a imagens falha com erro claro).
- **Validação real (usuário):** anexar imagem / capturar tela e conferir a análise.
- Webcam (StreamingSensor) e OCR dedicado (tesseract) — incrementos futuros.
- Captura só do monitor primário (multi-monitor via config).

## Checklist
- [x] Imagem no turno → LLM de visão (`vision_model`), pulando RAG
- [x] `ScreenCaptureSensor` (OnDemand) + `GET /api/vision/screen`
- [x] Frontend: anexar imagem, capturar tela, preview e exibição
- [x] Testes verdes (backend) e TS limpo (frontend)
- [ ] `ollama pull llava` + validação real do usuário
- [ ] Webcam e OCR dedicado (evolução)
