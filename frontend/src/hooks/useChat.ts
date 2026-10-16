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
import { captureScreen as apiCaptureScreen, runOcr as apiRunOcr } from "../services/api";
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
  /** Conversa ativa (memória de longo prazo). `null` = ainda não persistida. */
  conversationId: string | null;
  /** Começa uma conversa nova: limpa a tela; o próximo envio cria no banco. */
  newConversation: () => void;
  /** Retoma uma conversa: mostra o histórico e passa a enviar com o id dela. */
  resumeConversation: (id: string, messages: ChatMessage[]) => void;
  send: (text: string) => void;
  draft: string;
  setDraft: (text: string) => void;
  listening: boolean;
  toggleListening: () => void;
  autoSend: boolean;
  setAutoSend: (value: boolean) => void;
  speaking: boolean;
  stopSpeaking: () => void;
  muted: boolean;
  setMuted: (value: boolean) => void;
  pendingImage: string | null;
  attachImageFile: (file: File) => void;
  captureScreen: () => void;
  clearImage: () => void;
  /** OCR: lê o texto da imagem anexada (ou da tela) e joga no campo de mensagem. */
  ocr: () => void;
  ocrBusy: boolean;
  handsFree: boolean;
  setHandsFree: (value: boolean) => void;
  wakeWord: string;
  setWakeWord: (value: string) => void;
  requireWakeWord: boolean;
  setRequireWakeWord: (value: boolean) => void;
}

export interface UseChatOptions {
  /** Arquivos do projeto (caminhos relativos) a enviar como contexto de código. */
  contextFiles?: string[];
}

export function useChat(options: UseChatOptions = {}): UseChat {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<StatusState>("idle");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [turnActive, setTurnActive] = useState(false);
  const [pendingImage, setPendingImage] = useState<{ dataUrl: string; base64: string } | null>(null);
  const [ocrBusy, setOcrBusy] = useState(false);
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
  // Silenciar a voz da Friday (não tocar a fala automaticamente). Persistido.
  const [muted, setMutedState] = useState<boolean>(() => readBool("friday.muted", false));

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
  const mutedRef = useRef(muted);
  mutedRef.current = muted;
  const turnActiveRef = useRef(turnActive);
  turnActiveRef.current = turnActive;
  const pendingImageRef = useRef(pendingImage);
  pendingImageRef.current = pendingImage;
  const conversationIdRef = useRef(conversationId);
  conversationIdRef.current = conversationId;
  // Arquivos de contexto (workspace) vivem no App; um ref os expõe ao send
  // (inclusive quando o envio vem da voz).
  const contextFilesRef = useRef<string[]>(options.contextFiles ?? []);
  contextFilesRef.current = options.contextFiles ?? [];

  useEffect(() => audioPlayer.onChange(() => setSpeaking(audioPlayer.speaking)), []);
  const stopSpeaking = useCallback(() => audioPlayer.stop(), []);
  const setMuted = useCallback((value: boolean) => {
    setMutedState(value);
    writeBool("friday.muted", value);
    if (value) audioPlayer.stop(); // silencia imediatamente a fala em curso
  }, []);

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
    const ctx = contextFilesRef.current;
    try {
      socketRef.current.send(
        outText,
        img ? [img.base64] : undefined,
        ctx.length ? ctx : undefined,
        conversationIdRef.current ?? undefined,
      );
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

  // OCR: transcreve o texto da imagem anexada (upload) ou, se não houver, da
  // tela do Host, e o insere no campo de mensagem para o usuário editar/perguntar.
  const ocr = useCallback(async () => {
    const img = pendingImageRef.current;
    setOcrBusy(true);
    setError(null);
    try {
      const { text, chars } = img
        ? await apiRunOcr({ source: "upload", image: img.base64 })
        : await apiRunOcr({ source: "screen" });
      if (chars === 0) {
        setError("OCR não encontrou texto na imagem.");
        return;
      }
      setDraft((prev) => (prev.trim() ? `${prev}\n${text}` : text));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao executar o OCR.");
    } finally {
      setOcrBusy(false);
    }
  }, []);

  // Começa do zero: esvazia a tela e "esquece" a conversa atual. O próximo
  // envio, sem conversation_id, faz o backend criar uma conversa nova.
  const newConversation = useCallback(() => {
    audioPlayer.stop();
    setMessages([]);
    setConversationId(null);
    setError(null);
    setTurnActive(false);
  }, []);

  // Retoma uma conversa do histórico: mostra as mensagens já persistidas e passa
  // a enviar com o id dela (o backend semeia sua janela de contexto do banco no
  // próximo turno).
  const resumeConversation = useCallback(
    (id: string, history: ChatMessage[]) => {
      audioPlayer.stop();
      setMessages(history);
      setConversationId(id);
      setError(null);
      setTurnActive(false);
    },
    [],
  );

  const handleEvent = useCallback(
    (event: ServerEvent) => {
      switch (event.type) {
        case "status":
          setStatus(event.state);
          break;
        case "conversation":
          // Backend criou ou retomou a conversa: guarda o id p/ os próximos
          // turnos e para a barra lateral destacar/atualizar a ativa.
          setConversationId(event.id);
          break;
        case "sources":
          patchAssistant((m) => ({ ...m, sources: event.sources }));
          break;
        case "token":
          patchAssistant((m) => ({ ...m, content: m.content + event.content }));
          break;
        case "audio": {
          const url = `data:${event.mime};base64,${event.data}`;
          // Guarda o áudio (mantém o botão "Ouvir" para reprodução manual),
          // mas só toca automaticamente se a voz não estiver silenciada.
          patchAssistant((m) => ({ ...m, audioUrl: url }));
          if (!mutedRef.current) void audioPlayer.play(url);
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
    conversationId,
    newConversation,
    resumeConversation,
    send,
    draft,
    setDraft,
    listening,
    toggleListening,
    autoSend,
    setAutoSend,
    speaking,
    stopSpeaking,
    muted,
    setMuted,
    pendingImage: pendingImage?.dataUrl ?? null,
    attachImageFile,
    captureScreen: () => void captureScreen(),
    clearImage,
    ocr: () => void ocr(),
    ocrBusy,
    handsFree,
    setHandsFree,
    wakeWord,
    setWakeWord,
    requireWakeWord,
    setRequireWakeWord,
  };
}
