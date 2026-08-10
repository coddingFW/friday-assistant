// Hook que orquestra o chat: gerencia a conexão WebSocket, o estado das
// mensagens, os indicadores de status, o streaming de tokens e a escuta por voz
// (STT). A transcrição pode auto-enviar ou apenas preencher o campo — preferência
// do usuário, persistida em localStorage.

import { useCallback, useEffect, useRef, useState } from "react";
import { ChatSocket } from "../services/chatSocket";
import { audioPlayer } from "../services/audioPlayer";
import type { ChatMessage, ServerEvent, StatusState } from "../types";

let counter = 0;
const newId = (): string => `${Date.now()}-${counter++}`;

const AUTOSEND_KEY = "friday.autosend";
const readAutoSend = (): boolean => {
  try {
    return localStorage.getItem(AUTOSEND_KEY) === "1";
  } catch {
    return false;
  }
};

export interface UseChat {
  messages: ChatMessage[];
  status: StatusState;
  connected: boolean;
  error: string | null;
  send: (text: string) => void;
  draft: string;
  setDraft: (text: string) => void;
  listening: boolean;
  toggleListening: () => void;
  autoSend: boolean;
  setAutoSend: (value: boolean) => void;
}

export function useChat(): UseChat {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<StatusState>("idle");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [listening, setListening] = useState(false);
  const [autoSend, setAutoSendState] = useState<boolean>(readAutoSend);
  const socketRef = useRef<ChatSocket | null>(null);

  // Ref para ler a preferência atual dentro do handler sem reconectar o socket.
  const autoSendRef = useRef(autoSend);
  autoSendRef.current = autoSend;

  const setAutoSend = useCallback((value: boolean) => {
    setAutoSendState(value);
    try {
      localStorage.setItem(AUTOSEND_KEY, value ? "1" : "0");
    } catch {
      // Preferência é opcional; ignora se o storage não estiver disponível.
    }
  }, []);

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

  const handleEvent = useCallback(
    (event: ServerEvent) => {
      switch (event.type) {
        case "status":
          setStatus(event.state);
          if (event.state === "listening") setListening(true);
          else if (event.state === "idle") setListening(false);
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
        case "transcript": {
          const text = event.text.trim();
          if (!text) break;
          if (autoSendRef.current) {
            send(text);
          } else {
            setDraft((prev) => (prev ? `${prev} ${text}` : text));
          }
          break;
        }
        case "done":
          patchAssistant((m) => ({ ...m, pending: false }));
          break;
        case "error":
          setError(event.message);
          setListening(false);
          patchAssistant((m) => ({ ...m, pending: false }));
          break;
      }
    },
    [patchAssistant, send],
  );

  useEffect(() => {
    const socket = new ChatSocket({
      onOpen: () => {
        setConnected(true);
        setError(null);
      },
      onClose: () => {
        setConnected(false);
        setListening(false);
      },
      onEvent: handleEvent,
    });
    socket.connect();
    socketRef.current = socket;
    return () => socket.close();
  }, [handleEvent]);

  const toggleListening = useCallback(() => {
    const socket = socketRef.current;
    if (!socket?.connected) return;
    if (listening) {
      try {
        socket.stopListening();
      } catch {
        // conexão pode ter caído; o estado é reconciliado pelos eventos.
      }
      setListening(false);
    } else {
      // Gesto do usuário: destrava o áudio para a resposta falada depois.
      void audioPlayer.unlock();
      setError(null);
      try {
        socket.startListening();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Falha ao iniciar a escuta.");
      }
    }
  }, [listening]);

  return {
    messages,
    status,
    connected,
    error,
    send,
    draft,
    setDraft,
    listening,
    toggleListening,
    autoSend,
    setAutoSend,
  };
}
