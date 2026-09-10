# PHASE_REPORT_09 — Memória de longo prazo (persistência de conversas)

## Objetivos
Dar à Friday **memória entre sessões**: persistir conversas e mensagens em disco
e poder retomá-las, listá-las e apagá-las. Escopo desta fatia: **SQLite via
Repository Pattern + múltiplas conversas**. (Busca semântica/embeddings, cache,
múltiplos modelos, plugins e empacotamento ficam para incrementos futuros.)

## Arquivos criados
- `backend/memory/ports.py` — modelos `Conversation`/`StoredMessage` + porta
  `ConversationRepository` (Protocol assíncrona).
- `backend/memory/providers/sqlite.py` — `SqliteConversationRepository` (stdlib
  `sqlite3`, I/O em `asyncio.to_thread`, conexão única sob lock).
- `backend/memory/factory.py` — `create_conversation_repository(settings)`.
- `backend/memory/service.py` — `MemoryService` (fachada de domínio: título,
  janela de histórico ↔ `ChatMessage`, gravação do turno).
- `backend/api/rest/conversations.py` — `GET /api/conversations`,
  `GET /api/conversations/{id}`, `DELETE /api/conversations/{id}`.
- `ADR/ADR-0012.md`; `tests/test_memory.py`.

## Arquivos modificados
- `config/settings.py` — `memory_enabled` (default True), `db_path`
  (default `./data/friday.db`).
- `utils/errors.py` — `StorageError`.
- `api/dependencies.py` — `get_memory_service`.
- `api/rest/__init__.py` — registro do router de conversas.
- `api/websocket/protocol.py` — `conversation_id` na `UserMessage`; novo evento
  `conversation` (anuncia a conversa ativa/criada).
- `api/websocket/chat.py` — `_ensure_conversation` (cria/retoma + semeia a janela
  do banco) e persistência do turno em `_handle_turn`.
- `main.py` — cria o repositório/serviço no lifespan e fecha no shutdown.
- `.gitignore` — `/data/`, `*.db`, `*.sqlite3`. `PROJECT_MANIFEST.md` — Fase 9.

## Decisões de arquitetura
**ADR-0012**: memória longa em SQLite via Repository Pattern, no mesmo estilo
Ports & Adapters de `rag/`/`stt/`/`tts/`. `sqlite3` da stdlib (zero dependência
nova) com I/O em `asyncio.to_thread` para não bloquear o event loop. Múltiplas
conversas; recall = janela das últimas N mensagens (sem vetor). Só texto é
persistido no histórico (imagens são de uso único no turno).

## Como validado
- **Backend:** suíte com **80 testes verdes** (9 novos: repositório —
  roundtrip, janela/ordem de `recent_messages`, delete em cascata; serviço —
  derivação de título, `record_turn`/`history_window`; REST — list/get/delete e
  404; WebSocket — cria+persiste conversa e retoma semeando o histórico).
- **Boot real:** app sobe com o lifespan, `memory_service` ativo,
  `GET /api/conversations` responde 200. Banco criado sob `db_path`.
- Degradação: `FRIDAY_MEMORY_ENABLED=false` (ou falha do banco) volta ao
  histórico só-RAM sem derrubar o turno; testes de WS existentes seguem verdes.

## Frontend (concluído)
Barra lateral de histórico que torna a memória visível — o backend já expunha
todo o contrato (`conversation_id` no WS, evento `conversation`, REST list/get/
delete); o frontend passou a consumi-lo.
- `types.ts` — evento `conversation`, `conversation_id` na `UserMessage`, tipos
  REST (`ConversationSummary`/`ConversationMessage`/`ConversationDetail`).
- `services/api.ts` — `listConversations`/`getConversation`/`deleteConversation`
  (o DELETE trata o 204 sem corpo). `services/chatSocket.ts` — `send` carrega o
  `conversation_id`.
- `hooks/useChat.ts` — estado `conversationId` (setado pelo evento `conversation`
  e enviado a cada turno) + `newConversation()` e `resumeConversation(id, msgs)`.
- `hooks/useConversations.ts` — lista/refresh/apagar; recarrega quando a conversa
  ativa muda e ~500ms após o fim de cada turno (o backend persiste logo após o
  `idle` — o atraso evita a corrida), mantendo contagem/ordem em dia.
- `components/HistoryPanel.tsx` — nova conversa, lista com tempo relativo +
  contagem, retomar ao clicar, apagar com confirmação inline, ativa destacada.
- `App.tsx`/`components/Header.tsx` — botão "Histórico", painel no layout, retomar
  via REST, apagar a ativa limpa a tela. `styles.css` — painel `.hist`.
- **Validado:** `tsc` limpo e build de produção ok.

## Limitações / pendências
- Recall é por janela recente; sem busca semântica de conversas antigas.
- Sem paginação no `list_messages`/`list_conversations` (volume local baixo).

## Checklist
- [x] `backend/memory/` (porta + adapter SQLite + fábrica + serviço)
- [x] REST: listar / ler / apagar conversas
- [x] WebSocket: cria/retoma conversa (`conversation_id` + evento `conversation`)
      e persiste o turno; janela semeada do banco
- [x] Config `memory_enabled` / `db_path`; degradação graciosa
- [x] Testes verdes (80) e boot real validado
- [x] Frontend: barra lateral de histórico (listar/retomar/apagar + nova conversa)
