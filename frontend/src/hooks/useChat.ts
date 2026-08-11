// Hook que orquestra o chat: conexão WebSocket, mensagens, status, streaming e a
// voz (STT). Modos da voz:
//  - push-to-talk (clicar no mic): a transcrição auto-envia OU preenche o campo;
//  - mãos-livres: mic contínuo; só age quando a fala tem a wake word ("Friday").
// Anti-eco: enquanto a Friday processa/fala, o mic é pausado (não transcreve a
// própria voz). Preferências persistidas em localStorage.

import { useCallback, useEffect, useRef, useState } from "react";
import { ChatSocket } from "../services/chatSocket";
import { audioPlayer } from "../services/audioPlayer";
import { detectWake } from "../services/wakeWord";
import { captureScreen as apiCaptureScreen } from "../services/api";
import type { ChatMessage, ServerEvent, StatusState } from "../types";

let counter = 0;
const newId = (): string => `${Date.now()}-${counter++}`;

const readBool = (key: string, def: boolean): boolean => {
  try {
    const v = localStorage.getItem(key);
    return v === null ? def : v === "1";
  } catch {
    return def;
  }
};
const writeBool = (key: string, v: boolean): void => {
  try {
    localStorage.setItem(key, v ? "1" : "0");
  } catch {
    /* opcional */
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
  speaking: boolean;
  stopSpeaking: () => void;
  pendingImage: string | null;
  attachImageFile: (file: File) => void;
  captureScreen: () => void;
  clearImage: () => void;
  handsFree: boolean;
  setHandsFree: (value: boolean) => void;
  wakeWord: string;
  setWakeWord: (value: string) => void;
  requireWakeWord: boolean;
  setRequireWakeWord: (value: boolean) => void;
}

export function useChat(): UseChat {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<StatusState>("idle");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [turnActive, setTurnActive] = useState(false);
  const [pendingImage, setPendingImage] = useState<{ dataUrl: string; base64: string } | null>(null);
  const [autoSend, setAutoSendState] = useState<boolean>(() => readBool("friday.autosend", false));
  // Mãos-livres NÃO é persistido: ligar exige um gesto (destrava o áudio da fala).
  const [handsFree, setHandsFreeState] = useState(false);
  const [wakeWord, setWakeWordState] = useState<string>(() => {
    try {
      return localStorage.getItem("friday.wakeWord") ?? "Friday";
    } catch {
      return "Friday";
    }
  });
  const [requireWakeWord, setRequireWakeState] = useState<boolean>(() => readBool("friday.requireWake", true));

  const socketRef = useRef<ChatSocket | null>(null);
  const micOnRef = useRef(false);
  const prevHandsFree = useRef(false);

  // Refs para ler o estado atual dentro do handler sem reconectar o socket.
  const autoSendRef = useRef(autoSend);
  autoSendRef.current = autoSend;
  const handsFreeRef = useRef(handsFree);
  handsFreeRef.current = handsFree;
  const requireWakeRef = useRef(requireWakeWord);
  requireWakeRef.current = requireWakeWord;
  const wakeWordRef = useRef(wakeWord);
  wakeWordRef.current = wakeWord;
  const turnActiveRef = useRef(turnActive);
  turnActiveRef.current = turnActive;
  const pendingImageRef = useRef(pendingImage);
  pendingImageRef.current = pendingImage;

  useEffect(() => audioPlayer.onChange(() => setSpeaking(audioPlayer.speaking)), []);
  const stopSpeaking = useCallback(() => audioPlayer.stop(), []);

  const setAutoSend = useCallback((value: boolean) => {
    setAutoSendState(value);
    writeBool("friday.autosend", value);
  }, []);
  const setWakeWord = useCallback((value: string) => {
    setWakeWordState(value);
    try {
      localStorage.setItem("friday.wakeWord", value);
    } catch {
      /* opcional */
    }
  }, []);
  const setRequireWakeWord = useCallback((value: boolean) => {
    setRequireWakeState(value);
    writeBool("friday.requireWake", value);
  }, []);
  const setHandsFree = useCallback((value: boolean) => {
    if (value) {
      audioPlayer.stop();
      void audioPlayer.unlock(); // gesto do usuário destrava a fala futura
    }
    setHandsFreeState(value);
  }, []);

  // Liga/desliga o microfone de forma idempotente e reflete no indicador.
  const setMic = useCallback((on: boolean) => {
    const socket = socketRef.current;
    if (!socket?.connected) return;
    if (on === micOnRef.current) return;
    micOnRef.current = on;
    setListening(on);
    try {
      if (on) {
        audioPlayer.stop();
        void audioPlayer.unlock();
        socket.startListening();
      } else {
        socket.stopListening();
      }
    } catch {
      /* reconciliado pelos eventos/estado */
    }
  }, []);

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
    const img = pendingImageRef.current;
    if ((!content && !img) || !socketRef.current?.connected) return;
    const outText = content || "Descreva a imagem."; // backend exige texto
    audioPlayer.stop(); // barge-in
    void audioPlayer.unlock();
    setError(null);
    setTurnActive(true);
    setMessages((prev) => [
      ...prev,
      { id: newId(), role: "user", content: outText, image: img?.dataUrl },
      { id: newId(), role: "assistant", content: "", pending: true },
    ]);
    try {
      socketRef.current.send(outText, img ? [img.base64] : undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao enviar.");
      setTurnActive(false);
    }
    if (img) setPendingImage(null);
  }, []);

  const attachImageFile = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = typeof reader.result === "string" ? reader.result : "";
      const comma = dataUrl.indexOf(",");
      const base64 = comma >= 0 ? dataUrl.slice(comma + 1) : "";
      if (base64) setPendingImage({ dataUrl, base64 });
    };
    reader.readAsDataURL(file);
  }, []);

  const captureScreen = useCallback(async () => {
    try {
      const { image, mime } = await apiCaptureScreen();
      setPendingImage({ dataUrl: `data:${mime};base64,${image}`, base64: image });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao capturar a tela.");
    }
  }, []);

  const clearImage = useCallback(() => setPendingImage(null), []);

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
          void audioPlayer.play(url);
          break;
        }
        case "transcript": {
          const text = event.text.trim();
          if (!text) break;
          if (handsFreeRef.current) {
            // Anti-eco: ignora transcrições enquanto ela processa ou fala
            // (o backend segue captando durante o turno; o cliente não age).
            if (turnActiveRef.current || audioPlayer.speaking) break;
            if (requireWakeRef.current) {
              const { matched, command } = detectWake(text, wakeWordRef.current);
              if (matched && command) send(command);
            } else {
              send(text);
            }
          } else if (autoSendRef.current) {
            send(text);
          } else {
            setDraft((prev) => (prev ? `${prev} ${text}` : text));
          }
          break;
        }
        case "done":
          setTurnActive(false);
          patchAssistant((m) => ({ ...m, pending: false }));
          break;
        case "error":
          setError(event.message);
          setTurnActive(false);
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
        micOnRef.current = false;
        setListening(false);
      },
      onEvent: handleEvent,
    });
    socket.connect();
    socketRef.current = socket;
    return () => socket.close();
  }, [handleEvent]);

  // Mãos-livres: o mic fica ligado, mas pausa enquanto ela processa (turno ativo)
  // ou fala (anti-eco). No modo manual, este efeito não mexe no mic.
  const busy = turnActive || speaking;
  useEffect(() => {
    if (handsFree) {
      setMic(!busy);
    } else if (prevHandsFree.current) {
      setMic(false); // acabou de desligar o mãos-livres
    }
    prevHandsFree.current = handsFree;
  }, [handsFree, busy, connected, setMic]);

  const toggleListening = useCallback(() => {
    if (handsFreeRef.current) return; // no mãos-livres o mic é automático
    setMic(!micOnRef.current);
  }, [setMic]);

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
    speaking,
    stopSpeaking,
    pendingImage: pendingImage?.dataUrl ?? null,
    attachImageFile,
    captureScreen: () => void captureScreen(),
    clearImage,
    handsFree,
    setHandsFree,
    wakeWord,
    setWakeWord,
    requireWakeWord,
    setRequireWakeWord,
  };
}
