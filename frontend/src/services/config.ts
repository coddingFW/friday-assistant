// Endpoints do backend. O frontend fala EXCLUSIVAMENTE via REST/WebSocket —
// nunca acessa Ollama, banco ou serviços locais diretamente (regra do manifesto).

const DEFAULT_HOST = "127.0.0.1:8000";

// Permite sobrescrever via variável de ambiente do Vite (VITE_BACKEND_HOST).
const host = import.meta.env.VITE_BACKEND_HOST ?? DEFAULT_HOST;

export const REST_BASE_URL = `http://${host}/api`;
export const WS_CHAT_URL = `ws://${host}/ws/chat`;
