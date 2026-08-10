// Hook que orquestra o chat: gerencia a conexão WebSocket, o estado das
// mensagens, os indicadores de status e o streaming de tokens.

import { useCallback, useEffect, useRef, useState } from "react";
import { ChatSocket } from "../services/chatSocket";
import { audioPlayer } from "../services/audioPlayer";
import type { ChatMessage, ServerEvent, StatusState } from "../types";

let counter = 0;
const newId = (): string => `${Date.now()}-${counter++}`;

export interface UseChat {
  messages: ChatMessage[];
  status: StatusState;
  connected: boolean;
  error: string | null;
  send: (text: string) => void;
}

export function useChat(): UseChat {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<StatusState>("idle");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<ChatSocket | null>(null);

  // Atualiza a última mensagem do assistente (a que está sendo gerada).
  const patchAssistant = useCallback(
    (patch: (m: ChatMessage) => ChatMessage) => {
      setMessages((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === "assistant") {
            next[i] = patch(next[i]);
            break;
          }
        }
        return next;
      });
    },
    [],
  );

  const handleEvent = useCallback(
    (event: ServerEvent) => {
      switch (event.type) {
        case "status":
          setStatus(event.state);
          break;
        case "sources":
          patchAssistant((m) => ({ ...m, sources: event.sources }));
          break;
        case "token":
          patchAssistant((m) => ({ ...m, content: m.content + event.content }));
          break;
        case "audio": {
          const url = `data:${event.mime};base64,${event.data}`;
          patchAssistant((m) => ({ ...m, audioUrl: url }));
          // Toca pelo audioPlayer (roteado no AnalyserNode p/ o avatar animar).
          void audioPlayer.play(url);
          break;
        }
        case "done":
          patchAssistant((m) => ({ ...m, pending: false }));
          break;
        case "error":
          setError(event.message);
          patchAssistant((m) => ({ ...m, pending: false }));
          break;
      }
    },
    [patchAssistant],
  );

  useEffect(() => {
    const socket = new ChatSocket({
      onOpen: () => {
        setConnected(true);
        setError(null);
      },
      onClose: () => setConnected(false),
      onEvent: handleEvent,
    });
    socket.connect();
    socketRef.current = socket;
    return () => socket.close();
  }, [handleEvent]);

  const send = useCallback((text: string) => {
    const content = text.trim();
    if (!content || !socketRef.current?.connected) return;
    // Destrava o áudio no gesto do usuário (a fala chega segundos depois).
    void audioPlayer.unlock();
    setError(null);
    setMessages((prev) => [
      ...prev,
      { id: newId(), role: "user", content },
      { id: newId(), role: "assistant", content: "", pending: true },
    ]);
    try {
      socketRef.current.send(content);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao enviar.");
    }
  }, []);

  return { messages, status, connected, error, send };
}
