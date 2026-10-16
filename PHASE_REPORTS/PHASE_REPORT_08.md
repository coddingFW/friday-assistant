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
- [x] OCR dedicado (Tesseract) — ver adendo abaixo
- [ ] Webcam (evolução)

---

# Adendo — OCR dedicado (Tesseract) · set/2026 · ADR-0016

## Objetivo
Transcrever o **texto literal** de uma imagem (upload ou tela) via Tesseract,
100% local, sem depender do LLM de visão (que *interpreta*; o OCR *transcreve*).

## Arquivos criados
- `backend/perception/sensors/ocr.py` — `OcrSensor` (OnDemand, `pytesseract` +
  `Pillow`), motor injetável, emite `Percept(OCR_TEXT, text/plain)`.
- `ADR/ADR-0016.md`.

## Arquivos modificados
- `config/settings.py` — `ocr_enabled`, `ocr_lang` (`por+eng`), `ocr_tesseract_cmd`,
  `ocr_tessdata_dir` (usa `TESSDATA_PREFIX`; para tessdata gravável fora do sistema).
- `utils/errors.py` — `OcrUnavailableError(SensorError)`.
- `api/rest/vision.py` — `POST /api/vision/ocr` (`source` upload/screen, `image`,
  `lang`) → `{ text, lang, chars }`.
- `main.py` — registra o `OcrSensor` (se `vision_enabled` e `ocr_enabled`).
- `requirements.txt` — `pytesseract`.
- **Frontend:** `services/api.ts` (`runOcr`), `hooks/useChat.ts` (`ocr`/`ocrBusy`),
  `components/Composer.tsx` (botão 🔤 → texto lido cai no campo), `App.tsx` (wiring).
- `tests/test_vision.py` — 8 testes novos de OCR (motor injetado).

## Como validado
- **Backend:** suíte com **109 testes verdes** (8 novos: sensor extrai/apara texto,
  override de idioma, exige imagem; endpoint upload/screen, 400 sem imagem, 400
  base64 inválida, 503 sem Tesseract com orientação).
- **Frontend:** `tsc --noEmit` limpo; build de produção ok.

## Setup nesta máquina (set/2026)
- Tesseract v5.4.0 em `C:\Program Files\Tesseract-OCR` (fora do PATH →
  `FRIDAY_OCR_TESSERACT_CMD`). `pytesseract` instalado no venv.
- A pasta `tessdata` da instalação só tinha `eng`/`osd` e não é gravável; baixamos
  `por.traineddata` (oficial, ~15 MB) e montamos `models/tessdata/` (por+eng+osd,
  gitignored) apontado por `FRIDAY_OCR_TESSDATA_DIR`; `FRIDAY_OCR_LANG=por+eng`.
- **Validado ao vivo:** OCR ponta a ponta via `POST /api/vision/ocr` devolveu texto
  correto em inglês e em **português com acentos** ("Olá… Reunião às três… ação").

## Limitações / pendências
- Sem pré-processamento de imagem (deskew/threshold) por ora.
- Validação na UI (botão 🔤) pelo usuário no fluxo real ainda a fazer.
