# Friday — Frontend (Tauri 2.0 + React + TypeScript)

Interface da assistente. É um **web app puro** que fala com o backend
**exclusivamente via REST + WebSocket** (nunca acessa Ollama/banco/serviços
diretamente). O mesmo código roda no navegador (dev) e dentro do shell Tauri
(desktop; futuramente mobile).

## Requisitos
- Node.js 18+ (validado em 24).
- Para empacotar o desktop: **Rust** + WebView2 (Windows). Ver abaixo.

## Desenvolvimento (web — não exige Rust)
```bash
npm install
npm run dev
```
Abre em `http://127.0.0.1:1420`. Requer o **backend rodando** em `127.0.0.1:8000`:
```bash
cd ..
uvicorn backend.main:app --reload
```

## Desktop com Tauri (Windows)
Pré-requisitos (uma vez): **Rust** (`winget install Rustlang.Rustup`), **VS Build
Tools 2022 com o workload "Desktop development with C++"** (traz MSVC + Windows
SDK) e **WebView2** (já vem no Win11).

Compile com o script (encapsula as três pegadinhas — ver abaixo):
```powershell
./build-desktop.ps1 --no-bundle   # só o executável (rápido)
./build-desktop.ps1               # + instaladores (bundle)
```
Saída: `%LOCALAPPDATA%\friday-build\release\friday.exe`. Rode com o **backend no ar**.

### Pegadinhas de build no Windows (aprendidas em teste real)
1. **Ambiente MSVC**: rode via `vcvars64`/`build-desktop.ps1`, senão o rustc não
   acha `link.exe` (e, no Git-Bash, pega o `link` errado do GNU/coreutils).
2. **Windows SDK**: sem o workload "Desktop C++", falta `kernel32.lib` → erro
   de link `LNK1181`.
3. **OneDrive**: o `target/` do Rust **não pode** ficar dentro do OneDrive (o sync
   trava os arquivos → `output path is not a writable directory`). O script já
   redireciona via `CARGO_TARGET_DIR` para fora do OneDrive.

## Estrutura
```
frontend/
├── src/
│   ├── components/   # Header, MessageList, Composer, StatusIndicator, Sources
│   ├── hooks/        # useChat (estado + streaming)
│   ├── services/     # api.ts (REST), chatSocket.ts (WS), config.ts (URLs)
│   ├── types.ts      # contrato espelhando o protocolo do backend
│   ├── App.tsx  main.tsx  styles.css
├── src-tauri/        # shell Tauri 2.0 (Rust) — buildável onde houver Rust
└── vite.config.ts  package.json  tsconfig.json
```

## Configuração
`VITE_BACKEND_HOST` sobrescreve o host do backend (default `127.0.0.1:8000`) —
útil para o cliente mobile apontar ao Host na LAN.
