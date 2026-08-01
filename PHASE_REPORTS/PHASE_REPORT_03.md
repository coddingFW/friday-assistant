# PHASE_REPORT_03 — Interface (Fase 3)

## Objetivos
Implementar a interface aprovada (Tauri 2.0 + React + TypeScript), consumindo o
backend exclusivamente via REST/WebSocket, com streaming de resposta, indicadores
de estado e exibição de fontes (RAG). Incluir warm-up do modelo no backend.

## Arquivos criados
### Frontend (`frontend/`)
- `package.json`, `index.html`, `vite.config.ts`, `tsconfig*.json`, `.gitignore`, `README.md`.
- `src/main.tsx`, `src/App.tsx`, `src/styles.css`, `src/types.ts`, `src/vite-env.d.ts`.
- `src/services/`: `config.ts` (URLs), `api.ts` (REST), `chatSocket.ts` (WS tipado).
- `src/hooks/useChat.ts` (estado + streaming).
- `src/components/`: `Header`, `StatusIndicator`, `MessageList`, `Composer`, `Sources`.
- `src-tauri/`: `tauri.conf.json`, `Cargo.toml`, `build.rs`, `src/{main,lib}.rs`.

### Backend (warm-up + correções)
- `brain/providers/ollama_provider.py` — método `warmup()`.
- `config/settings.py` — `ollama_warmup`; `ollama_read_timeout` 120→300s; `rag_timeout` 10→20s.
- `main.py` — warm-up em segundo plano no lifespan.
- `brain/conversation.py` — remoção de `yield` em `finally` (fix GeneratorExit).
- `api/websocket/chat.py` — `_handle_turn` resiliente à desconexão (aclose do gerador).

## Dependências
Frontend: react, react-dom, vite, @vitejs/plugin-react, typescript, @tauri-apps/cli.
Backend: nenhuma nova.

## Como validado
- **TypeScript** compila limpo (`tsc --noEmit`, exit 0).
- **Testes backend**: 37 verdes (36 + regressão de fechamento no meio do streaming).
- **Validação real no navegador** (Vite dev + backend + Ollama + `llama3.1:8b`):
  pergunta → status *Buscando* → **3 fontes reais** → *Respondendo* → resposta
  real em streaming citando as fontes → *Ocioso*. **Sem crashes.**

## Problemas encontrados e corrigidos (via teste real)
1. **Crash na desconexão em streaming** (`websocket.send after close` +
   "async generator ignored GeneratorExit"). Corrigido: handler resiliente +
   `ConversationService` sem `yield` em `finally`.
2. **Busca RAG estourando 10s** (agregação multi-motor da `ddgs`). Timeout → 20s;
   degradação graciosa já cobria o caso.
3. **Cold start** do modelo excedendo o read timeout. Timeout → 300s + warm-up.

## Desktop Tauri — compilado com sucesso
Após instalar Rust + VS Build Tools (workload C++ com Windows SDK), o binário foi
gerado: `friday.exe` (8 MB), `Finished release in 18m46s`. Ícones gerados via
`tauri icon` (inclui Android/iOS). Script reutilizável: `frontend/build-desktop.ps1`.
Três pegadinhas resolvidas e documentadas: ambiente MSVC (vcvars), Windows SDK
(LNK1181) e `target/` fora do OneDrive (`CARGO_TARGET_DIR`). Ver `frontend/README.md`.

## Limitações
- Build do desktop **não pode** rodar com `target/` dentro do OneDrive (resolvido
  via `CARGO_TARGET_DIR`); ideal mover o projeto para fora do OneDrive.
- `tauri build` completo (instaladores) ainda não executado — só o executável
  (`--no-bundle`); o bundle baixa NSIS/WiX na primeira vez.
- Latência de geração em CPU é alta (~2 min p/ respostas com contexto); melhora
  com GPU ou modelo menor (configurável).

## Checklist
- [x] Interface Tauri 2.0 + React + TS
- [x] Comunicação só via REST/WebSocket (frontend desacoplado)
- [x] Streaming de tokens + indicadores (Ouvindo/Pensando/Buscando/Respondendo)
- [x] Exibição de fontes (RAG)
- [x] Warm-up do modelo (backend)
- [x] Resiliência a desconexão
- [x] Validação real no navegador (fluxo completo)

## Melhorias futuras / Pendências
- Instalar Rust e gerar os ícones para empacotar o desktop (`tauri build`).
- Seleção de modelo na UI (consumindo `GET /api/llm/models`).
- Persistência/histórico de conversas (REST) quando houver banco.
- Reconexão automática do WebSocket com backoff.
