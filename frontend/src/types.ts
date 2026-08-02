// Contrato de protocolo espelhando backend/api/websocket/protocol.py.
// Manter sincronizado com o backend (fonte da verdade do contrato).

export type StatusState = "thinking" | "searching" | "responding" | "idle";

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

export type ServerEvent =
  | StatusEvent
  | SourcesEvent
  | TokenEvent
  | AudioEvent
  | DoneEvent
  | ErrorEvent;

// Cliente -> Servidor (WebSocket)
export interface UserMessage {
  type: "user_message";
  content: string;
  model?: string;
}

// Modelo de UI
export type Role = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  sources?: Source[];
  audioUrl?: string;
  pending?: boolean;
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
