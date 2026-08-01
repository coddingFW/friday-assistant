# PHASE_REPORT_01 — Infraestrutura (Fase 1)

## Objetivos
Criar a base do backend: estrutura do projeto, FastAPI, configuração central,
logging estruturado e comunicação com o Ollama (via Strategy Pattern).

## Arquivos criados
### Backend
- `backend/__init__.py` — versão do pacote.
- `backend/config/settings.py` — configuração `pydantic-settings` (prefixo `FRIDAY_`).
- `backend/utils/logging.py` — logging estruturado (structlog, console/JSON).
- `backend/utils/errors.py` — hierarquia de exceções do domínio.
- `backend/brain/ports.py` — porta `LLMProvider` + `ChatMessage` (Ports & Adapters).
- `backend/brain/providers/ollama_provider.py` — adapter do Ollama (chat/tags/version).
- `backend/brain/factory.py` — fábrica de provedores (Strategy Pattern).
- `backend/api/dependencies.py` — injeção de dependência (`get_llm_provider`).
- `backend/api/rest/{health,llm}.py` — REST: saúde, config e modelos.
- `backend/api/websocket/{protocol,chat}.py` — WebSocket: streaming do LLM + status.
- `backend/main.py` — application factory + lifespan (DI raiz) + CORS.

### Suporte e testes
- `requirements.txt`, `requirements-dev.txt`, `.env.example`, `.gitignore`, `pytest.ini`, `README.md`.
- `tests/`: `conftest.py` (provedor falso + cliente ASGI), `test_config.py`,
  `test_health.py`, `test_ollama_provider.py`, `test_ws_chat.py`.

## Dependências
Runtime: fastapi, uvicorn[standard], pydantic, pydantic-settings, httpx, structlog.
Dev: pytest, pytest-asyncio.

## Como validado
- `pytest`: **14 testes, 100% passando** (Python 3.14.5).
- Smoke real: lifespan inicializa provider; `/api/health` responde 200 com
  `llm_reachable: false` quando o Ollama está offline (degradação graciosa).

## Checklist
- [x] Estrutura do projeto
- [x] FastAPI (REST + WebSocket)
- [x] Configuração central (pydantic-settings)
- [x] Logging estruturado (structlog)
- [x] Comunicação com Ollama (adapter + Strategy)
- [x] Testes automatizados verdes
- [x] Degradação graciosa sem Ollama

## Riscos / Limitações
- Ollama ainda **não instalado** no Host: geração real de texto indisponível até
  instalar o serviço e baixar `llama3.1:8b`.
- `TestClient` emite `StarletteDeprecationWarning` (httpx) — cosmético, sem impacto.
- Sem persistência ainda (SQLite entra em fase posterior).

## Alteração arquitetural aprovada durante a fase (ADR-0004)
Friday tornou-se **Assistente Multimodal Local**. Foi adicionada a **camada de
percepção** (`backend/perception/`), preparando a arquitetura para múltiplos sentidos
sem refatoração futura. Escopo desta fase: **apenas abstrações** (nenhum sensor
concreto, nenhuma visão computacional, nenhuma dependência nova).

Arquivos criados: `perception/{modality,ports,registry,manager}.py`,
`api/rest/sensors.py`, `tests/test_perception.py`. Alterados: `brain/ports.py` e
`ollama_provider.py` (campo `ChatMessage.images` multimodal-ready), `main.py`
(inicializa `SensorManager`), `api/dependencies.py`, `utils/errors.py`.

Validação: suíte passou de 14 → **23 testes verdes**, cobrindo streaming,
captura on-demand, injeção externa, rejeições, listagem via REST e payload
multimodal do LLM.

O plano de fases foi revisado: nova **Fase 8 (Visão/Multimodalidade)**; Evolução
passou a **Fase 9** (ver PROJECT_MANIFEST).

## Melhorias futuras / Pendências
- Fase 2: RAG (duckduckgo-search top-3 → contexto → Ollama).
- Instalar Ollama + modelo no Host para teste ponta a ponta com geração real.
- Fase 8: primeiros sensores concretos (webcam/tela/OCR) como adapters da camada.
- (Opcional) endpoint REST de histórico quando houver persistência.
