# PHASE_REPORT_10 — Workspace de código (projeto local, leitura) + modelo de código

## Objetivos
Deixar a Friday **boa em ensinar programação** e capaz de **trabalhar sobre um
projeto local**: apontar uma pasta, ler/buscar no código e responder com base nos
arquivos, usando um modelo de código. Escopo desta fatia: **somente leitura** (ela
lê e ensina; não escreve) + **roteamento para o modelo de código**. (Frontend e
escrita de arquivos ficam para depois.)

## Arquivos criados
- `backend/workspace/ports.py` — `TreeEntry`/`FileContent`/`SearchHit` + porta
  `WorkspaceProvider`.
- `backend/workspace/providers/local_fs.py` — `LocalFsWorkspace` (leitura confinada
  à raiz, ignora ruído, recusa binário, I/O em `asyncio.to_thread`).
- `backend/workspace/factory.py`, `backend/workspace/service.py`
  (`WorkspaceService` — fachada + `build_context_blocks` com orçamento).
- `backend/api/rest/workspace.py` — `root` (GET/POST), `tree`, `file`, `search`.
- `ADR/ADR-0013.md`; `tests/test_workspace.py`.

## Arquivos modificados
- `config/settings.py` — `code_model` (default `qwen2.5-coder:7b`),
  `code_system_prompt` (foco em ensinar), `workspace_enabled`, limites e
  `workspace_ignore_dirs`.
- `utils/errors.py` — `WorkspaceError`.
- `api/dependencies.py` — `get_workspace_service`.
- `api/rest/__init__.py` — registro do router de workspace.
- `api/websocket/protocol.py` — `context_files` na `UserMessage`.
- `api/websocket/chat.py` — lê os arquivos do projeto → `context_blocks` e passa
  ao turno.
- `brain/conversation.py` — turno de código: pula RAG, usa `code_model` e o prompt
  de ensino. `rag/service.py` — `build_code_messages`.
- `main.py` — cria o `WorkspaceService` no lifespan. `PROJECT_MANIFEST.md` — Fase 10.

## Decisões de arquitetura
**ADR-0013**: camada `workspace/` (Ports & Adapters), somente leitura e confinada
à raiz (bloqueia `..`/symlink); roteamento por contexto (mesmo padrão da visão):
`context_files` na mensagem ⇒ turno de código (modelo `qwen2.5-coder:7b` + prompt
de ensino + RAG pulado), preservando o `llama3.1` para conversa geral.

## Como validado
- **Backend:** suíte com **91 testes verdes** (11 novos: set_root valida;
  árvore ignora ruído; leitura + truncamento; recusa de binário; **bloqueio de
  escape de caminho**; busca; orçamento de contexto; roteamento usa `code_model`
  e pula RAG; REST completo + escape via REST = 400).
- **Boot real:** app sobe, workspace ativo; `POST /api/workspace/root`, `tree`,
  `file` respondem; `../../.env` via `file` retorna **400** (confinamento).
- `qwen2.5-coder:7b` instalado no Ollama.

## Frontend (concluído)
- `services/api.ts` (REST do workspace), `types.ts` (`context_files`, tipos Ws*),
  `services/chatSocket.ts` (envia `context_files`), `hooks/useChat.ts` (contexto
  no turno), `hooks/useWorkspace.ts` (raiz/árvore/seleção persistidas),
  `components/WorkspacePanel.tsx` (painel: apontar pasta + árvore + seleção),
  `App.tsx`/`Header.tsx` (botão "Projeto", badge "modo código", layout com painel),
  `Composer.tsx` (chip "N arquivos no contexto"), `styles.css`.
- **Validado ao vivo:** apontar `C:\dev\friday\backend` → árvore carrega
  (ignorando ruído), selecionar arquivo marca o contexto, chip + "modo código"
  aparecem. `tsc` limpo e build de produção ok.

## Limitações / pendências
- **Somente leitura:** a Friday não edita arquivos. Escrita (com confirmação,
  restrita à raiz, backup/git) é um incremento futuro.
- Raiz do workspace é única e por processo (app local de um usuário).
- Busca é textual simples (sem índice); ok para projetos pequenos/médios.

## Checklist
- [x] Camada `workspace/` (porta + adapter local + fábrica + serviço)
- [x] Segurança: acesso confinado à raiz (bloqueia `..`/symlink), binário recusado
- [x] REST: abrir pasta / árvore / ler arquivo / buscar
- [x] Turno de código: `context_files` → `code_model` + prompt de ensino + RAG pulado
- [x] `qwen2.5-coder:7b` como modelo de código (config)
- [x] Testes verdes (91) e boot real validado
- [x] Frontend: apontar pasta + árvore + seleção de contexto (validado ao vivo)
- [ ] Escrita/edição de arquivos com confirmação (futuro)
