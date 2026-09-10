// Cliente WebSocket tipado do chat. Encapsula a conexão e despacha eventos
// do servidor para callbacks. Toda comunicação em tempo real passa por aqui.

import { WS_CHAT_URL } from "./config";
import type { ServerEvent, UserMessage } from "../types";

export interface ChatSocketHandlers {
  onOpen?: () => void;
  onClose?: () => void;
  onEvent: (event: ServerEvent) => void;
}

export class ChatSocket {
  private ws: WebSocket | null = null;

  constructor(private readonly handlers: ChatSocketHandlers) {}

  connect(): void {
    if (this.ws && this.ws.readyState <= WebSocket.OPEN) return;
    const ws = new WebSocket(WS_CHAT_URL);
    ws.onopen = () => this.handlers.onOpen?.();
    ws.onclose = () => this.handlers.onClose?.();
    ws.onmessage = (ev) => {
      try {
        this.handlers.onEvent(JSON.parse(ev.data) as ServerEvent);
      } catch {
        // Ignora frames malformados; o backend é a fonte do contrato.
      }
    };
    this.ws = ws;
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  send(
    content: string,
    images?: string[],
    contextFiles?: string[],
    conversationId?: string,
  ): void {
    if (!this.connected) throw new Error("WebSocket não conectado.");
    const message: UserMessage = {
      type: "user_message",
      content,
      ...(images && images.length ? { images } : {}),
      ...(contextFiles && contextFiles.length ? { context_files: contextFiles } : {}),
      ...(conversationId ? { conversation_id: conversationId } : {}),
    };
    this.ws!.send(JSON.stringify(message));
  }

  startListening(): void {
    if (!this.connected) throw new Error("WebSocket não conectado.");
    this.ws!.send(JSON.stringify({ type: "listen_start" }));
  }

  stopListening(): void {
    if (!this.connected) return;
    this.ws!.send(JSON.stringify({ type: "listen_stop" }));
  }

  close(): void {
    this.ws?.close();
    this.ws = null;
  }
}
