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

## Desktop com Tauri (exige Rust)
Instale o Rust (https://rustup.rs) e, no Windows, o WebView2 (já vem no Win11):
```bash
npm run tauri dev     # janela nativa em modo dev
npm run tauri build   # instaladores (precisa de ícones em src-tauri/icons/)
```
> `cargo` não está instalado neste ambiente, por isso o shell Tauri não foi
> compilado aqui — a interface foi validada no navegador contra o backend real.

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
