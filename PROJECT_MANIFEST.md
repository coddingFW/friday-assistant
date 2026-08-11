# PROJECT_MANIFEST — Friday (Assistente Virtual Local)

> Documento de arquitetura **oficial e permanente**. Só pode ser alterado quando
> uma decisão arquitetural for aprovada (gera um ADR).

## Identidade
- **Projeto:** Friday — **Assistente Multimodal Local**
- **Plataforma alvo:** Windows (v1) → macOS → Linux → Cliente Mobile (LAN) → Web (futuro)
- **Princípio central:** 100% local/offline sempre que possível.
- **Multimodalidade:** a arquitetura nasce preparada para múltiplas modalidades de
  entrada (voz, webcam, tela, imagens, OCR, sensores futuros) via uma camada de
  percepção abstrata. Ver ADR-0004.

## Topologia
**Host + Clientes finos.** O backend e os serviços locais (LLM, STT, TTS) rodam
no Host (PC). Clientes (desktop co-locado hoje; mobile na LAN no futuro) são
apenas apresentação e falam com o Host via REST + WebSocket.

## Camadas
1. **Apresentação (Frontend):** telas, histórico, config, avatar, notificações. **Zero regra de negócio.**
2. **Aplicação/Domínio (Backend):** toda a regra de negócio (IA, RAG, memória, STT, TTS, avatar, eventos).
3. **Percepção (Sensors):** abstração de todas as entradas sensoriais. O Brain
   consome percepções **apenas** do `SensorManager`, nunca de um dispositivo.
4. **Serviços Locais (Infra):** Ollama, Whisper, Piper, SQLite, dispositivos.

O frontend **nunca** acessa diretamente Ollama, banco ou serviços locais — apenas a API do backend.
O Brain **nunca** acessa diretamente webcam, microfone ou tela — apenas a camada de percepção.

### Camada de percepção (Sensors)
- **Vocabulário único:** `Percept` (unidade normalizada) + `Modality` (text, audio,
  image, video, screen, ocr_text, signal). Toda entrada — de sensor local do Host
  **ou** de cliente remoto — vira um `Percept`.
- **Contratos:** `StreamingSensor` (mic, webcam) e `OnDemandSensor` (screenshot,
  leitura de imagem, OCR), via Ports & Adapters + Strategy.
- **Extensibilidade:** `SensorRegistry` registra novos sensores sem tocar no núcleo.
- **Ponto único:** `SensorManager` faz o fan-in; o Brain só consome de `perceive()`.
- **LLM multimodal:** `ChatMessage.images` (base64) já previsto para modelos de
  visão locais (ex.: llava via Ollama), sem impacto no fluxo somente-texto.

## Stack tecnológica (decisões permanentes)
| Área | Escolha | ADR |
|---|---|---|
| Linguagem | Python 3.12+ | — |
| Backend | FastAPI + Uvicorn | — |
| Config | pydantic-settings (prefixo `FRIDAY_`) | — |
| Logging | structlog (console/JSON por config) | — |
| LLM | Ollama local (default `llama3.1:8b`, trocável por config) | ADR-0002 |
| RAG | `ddgs` (DuckDuckGo, top-3), atrás de porta | ADR-0005 |
| STT | faster-whisper (Whisper) | ADR-0002 |
| TTS | Piper (`piper-tts`); sintetiza no Host, toca no cliente | ADR-0003, ADR-0007 |
| Frontend | Tauri 2.0 + React (TS), web app puro (REST/WS) | ADR-0001, ADR-0006 |
| Percepção | Camada `perception/` (Ports & Adapters + Strategy) | ADR-0004 |
| Banco | SQLite via Repository Pattern | — (Fase 9) |

## Comunicação
- **REST:** configuração, CRUD, histórico, perfis, persistência.
- **WebSocket:** todo tempo real — streaming do LLM, transcrição parcial,
  status ("Ouvindo/Pensando/Respondendo"), progresso do TTS, sincronização do
  avatar, notificações. **Nunca polling quando WebSocket for suficiente.**

## Padrões de engenharia
Clean Architecture (Ports & Adapters) · SOLID · DRY · KISS · Separation of
Concerns · Dependency Injection (FastAPI `Depends`) · Repository Pattern ·
Strategy Pattern (provedor de LLM, STT, TTS).

## Restrições absolutas
Proibido: OpenAI, Anthropic, Gemini, Azure OpenAI, ElevenLabs, Google Cloud,
Amazon Polly, Microsoft Azure Speech, qualquer API paga ou dependente de chave.
Todas as soluções são locais.

## Plano de fases (revisado após ADR-0004)
| Fase | Tema |
|---|---|
| 0 | Arquitetura ✅ |
| 1 | Infraestrutura (FastAPI, config, logging, Ollama, **camada de sensores**) ✅ |
| 2 | RAG (busca top-3 → contexto → Ollama, streaming via WS) ✅ |
| 3 | Interface (Tauri + React, web app puro; chat streaming + fontes) ✅ |
| 4 | Voz — TTS (Piper): síntese no Host, áudio via WS, toca no cliente ✅ |
| 5 | Avatar (frontend; expressão por status + lip-sync por amplitude) ✅ |
| 6 | STT (microfone → primeiro `StreamingSensor` concreto) ✅ |
| 7 | Loop contínuo (multimodal-aware) — mãos-livres + wake word ✅ |
| **8** | **Visão / Multimodalidade** (captura de tela + imagem → LLM de visão ✅; webcam/OCR a seguir) — habilitada pela camada de sensores |
| 9 | Evolução (memória longa, cache, múltiplos modelos, plugins, empacotamento) |

## Convenções
- Código, imports absolutos a partir de `backend`.
- Execução do backend: `uvicorn backend.main:app` a partir de `assistant-ai/`.
- Variáveis de ambiente com prefixo `FRIDAY_`; `.env` nunca versionado.
- Erros de infraestrutura são traduzidos para exceções de `backend.utils.errors`.
