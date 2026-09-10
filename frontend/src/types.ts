// Contrato de protocolo espelhando backend/api/websocket/protocol.py.
// Manter sincronizado com o backend (fonte da verdade do contrato).

export type StatusState =
  | "thinking"
  | "searching"
  | "responding"
  | "idle"
  | "listening";

export interface Source {
  title: string;
  url: string;
}

// Servidor -> Cliente (WebSocket)
export interface StatusEvent {
  type: "status";
  state: StatusState;
}
export interface SourcesEvent {
  type: "sources";
  sources: Source[];
}
export interface TokenEvent {
  type: "token";
  content: string;
}
export interface AudioEvent {
  type: "audio";
  mime: string;
  data: string; // base64
}
export interface DoneEvent {
  type: "done";
}
export interface ErrorEvent {
  type: "error";
  message: string;
}
export interface TranscriptEvent {
  type: "transcript";
  text: string;
  final: boolean;
}
export interface ConversationEvent {
  type: "conversation";
  id: string;
  title: string;
}

export type ServerEvent =
  | StatusEvent
  | SourcesEvent
  | TokenEvent
  | AudioEvent
  | DoneEvent
  | ErrorEvent
  | TranscriptEvent
  | ConversationEvent;

// Cliente -> Servidor (WebSocket)
export interface UserMessage {
  type: "user_message";
  content: string;
  model?: string;
  images?: string[]; // base64 (sem prefixo data:) para o LLM de visão
  context_files?: string[]; // arquivos do projeto a incluir como contexto (código)
  conversation_id?: string; // conversa a retomar (memória de longo prazo — Fase 9)
}
export interface ListenStart {
  type: "listen_start";
}
export interface ListenStop {
  type: "listen_stop";
}

// Modelo de UI
export type Role = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  sources?: Source[];
  audioUrl?: string;
  image?: string; // data URL da imagem anexada (exibição)
  pending?: boolean;
}

// Workspace (projeto local — Fase 10)
export interface WsRoot {
  root: string | null;
}
export interface WsTreeEntry {
  path: string; // relativo à raiz, separador "/"
  name: string;
  is_dir: boolean;
  size: number;
}
export interface WsFile {
  path: string;
  text: string;
  truncated: boolean;
  size: number;
}
export interface WsWriteResult {
  path: string;
  created: boolean;
  bytes_written: number;
  backup_path: string | null;
}

// Conversas (histórico / memória de longo prazo — Fase 9)
export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
  message_count: number;
}
export interface ConversationMessage {
  role: Role;
  content: string;
  model?: string | null;
  created_at: string; // ISO 8601
}
export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[];
}

// REST
export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  llm_provider: string;
  llm_model: string;
  llm_reachable: boolean;
}
