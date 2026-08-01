# Friday — Assistente Virtual Local

Assistente virtual executada 100% localmente (LLM, voz, avatar e interface).
Backend independente da interface; comunicação via **REST** (config/CRUD) e
**WebSocket** (tempo real). Arquitetura **Host + Clientes finos**.

> Estado atual: **Fase 1 — Infraestrutura** concluída (FastAPI, config, logging,
> comunicação com Ollama). Ver `PHASE_REPORTS/` e `PROJECT_MANIFEST.md`.

## Requisitos
- Python 3.12+ (validado em 3.14).
- [Ollama](https://ollama.com) instalado no Host, com um modelo baixado:
  ```bash
  ollama pull llama3.1:8b
  ```

## Instalação
Setup por máquina (venv + frontend + verificação do Ollama) em um comando —
ver **[SETUP.md](SETUP.md)**:
```powershell
./setup.ps1
```
Ou manualmente:
```bash
cd assistant-ai
python -m venv .venv
.venv/Scripts/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env            # ajuste se necessário
```

## Executar o backend
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
- Documentação interativa: `http://127.0.0.1:8000/docs`
- Saúde: `http://127.0.0.1:8000/api/health`

## Testar
```bash
pytest
```

## Estrutura
```
assistant-ai/
├── backend/
│   ├── api/{rest,websocket}/   # interfaces de entrada (sem regra de negócio)
│   ├── brain/                  # LLM: porta + adapter Ollama + fábrica (Strategy)
│   ├── config/                 # configuração central (pydantic-settings)
│   ├── utils/                  # logging estruturado + erros do domínio
│   └── main.py                 # app factory + lifespan (DI)
├── tests/                      # pytest (14 testes)
├── ADR/  PHASE_REPORTS/  docs/
└── PROJECT_MANIFEST.md
```

## Configuração
Todas as variáveis usam o prefixo `FRIDAY_` (ver `.env.example`). Trocar o modelo
do LLM é apenas configuração:
```bash
FRIDAY_LLM_MODEL=qwen3
```

## Restrições
100% local/offline. Proibido qualquer serviço pago ou dependente de chave de API
(OpenAI, Anthropic, Gemini, ElevenLabs, Google/Azure/AWS etc.).
