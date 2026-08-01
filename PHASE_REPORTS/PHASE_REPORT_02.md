# PHASE_REPORT_02 — RAG (Fase 2)

## Objetivos
Implementar RAG: busca DuckDuckGo, recuperação dos 3 melhores resultados,
construção do contexto e consulta ao Ollama — integrando ao chat em tempo real.

## Arquivos criados
### RAG
- `backend/rag/ports.py` — `SearchResult` + porta `SearchProvider` (Strategy).
- `backend/rag/providers/duckduckgo.py` — adapter `ddgs` (thread + timeout).
- `backend/rag/factory.py` — seleção do provedor por configuração.
- `backend/rag/context.py` — `build_context` (top-N → bloco textual com fontes).
- `backend/rag/service.py` — `RagService` (retrieve + build_messages).

### Orquestração (Brain)
- `backend/brain/events.py` — eventos de domínio do turno.
- `backend/brain/conversation.py` — `ConversationService` (RAG + LLM, streaming).

### Testes
- `tests/test_rag.py`, `tests/test_conversation.py`, `tests/test_ws_chat.py` (reescrito).

## Arquivos modificados
- `config/settings.py` — bloco RAG (`rag_enabled`, `rag_max_results`, região,
  timeout, `rag_system_prompt`).
- `api/websocket/{protocol,chat}.py` — evento `sources`, estado `searching`, e
  handler fino que traduz eventos de domínio.
- `api/dependencies.py`, `main.py` — DI e wiring do `ConversationService`.
- `utils/errors.py` — `RagError`, `SearchUnavailableError`.
- `requirements.txt`, `.env.example`.

## Dependências
Adicionada: **`ddgs`** (sucessor mantido do `duckduckgo-search`). Nenhuma outra.

## Como validado
- **35 testes verdes** (23 → 35): contexto, serviço RAG, fábrica, ConversationService
  (fluxo completo, sem-RAG, degradação de busca, falha de LLM) e WebSocket (fluxo
  com RAG, degradação, mensagem inválida).
- **Busca real ao vivo** contra o DuckDuckGo retornou os 3 melhores resultados.
- Boot real: startup loga `rag_enabled=True rag_provider=duckduckgo`.
- **Ponta a ponta REAL** (Ollama 0.32.5 + `llama3.1:8b`): `ConversationService`
  fez busca → contexto → **geração real em streaming** (51 tokens, resposta
  coerente citando a fonte [1]). Fluxo das Fases 1–2 comprovado com texto real.

## Ajuste de robustez (durante a validação real)
O primeiro E2E falhou por **cold start + prefill de prompt grande (RAG) em CPU**
estourando o timeout de leitura de 120s. Default de `ollama_read_timeout` elevado
para **300s** (`settings.py` + `.env.example`). Segundo E2E, com modelo quente,
concluiu com sucesso.

## Fluxo entregue
```
user_message ─► ConversationService.run()
   thinking → searching → (sources) → responding → tokens… → done → idle
        │            │                        │
        │       RagService.retrieve()    LLMProvider.stream_chat(
        │       (ddgs, top-3)              system+contexto+user)
        └─ WebSocket traduz eventos de domínio → protocolo do cliente
```

## Checklist
- [x] DuckDuckGo Search (via `ddgs`, atrás de porta)
- [x] Recuperação dos 3 melhores resultados
- [x] Construção do contexto
- [x] Consulta ao Ollama com contexto
- [x] Integração ao chat em tempo real (WebSocket)
- [x] Degradação graciosa (busca falha → responde sem fontes)
- [x] Testes verdes + busca real validada

## Riscos / Limitações
- `ddgs` pode sofrer rate-limit/instabilidade — mitigado por timeout, isolamento
  atrás da porta e degradação graciosa.
- Geração real de texto ainda depende de instalar o Ollama + modelo no Host.
- Sem re-ranqueamento/deduplicação de resultados (suficiente para o escopo da fase).

## Melhorias futuras / Pendências
- Heurística para decidir *quando* buscar (nem toda pergunta precisa de web).
- Cache de buscas recentes (Fase 9 — Evolução).
- Extração de conteúdo das páginas (além do snippet) para contexto mais rico.
