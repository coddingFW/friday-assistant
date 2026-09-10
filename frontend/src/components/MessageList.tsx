import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../types";
import { audioPlayer } from "../services/audioPlayer";
import { Sources } from "./Sources";
import { Markdown } from "./Markdown";

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);
  // Imagem ampliada no lightbox (null = fechado).
  const [zoom, setZoom] = useState<string | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Fecha o lightbox com Esc.
  useEffect(() => {
    if (!zoom) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setZoom(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoom]);

  if (messages.length === 0) {
    return (
      <div className="empty">
        <p className="empty__title">Olá! Eu sou a Friday.</p>
        <p className="empty__hint">
          Pergunte algo — eu busco na web e respondo com um modelo local.
        </p>
      </div>
    );
  }

  return (
    <div className="messages">
      {messages.map((m) => (
        <div key={m.id} className={`msg msg--${m.role}`}>
          <div className="msg__bubble">
            {m.image ? (
              <img
                className="msg__image"
                src={m.image}
                alt="imagem enviada"
                title="Clique para ampliar"
                onClick={() => setZoom(m.image!)}
              />
            ) : null}
            {m.role === "assistant" ? (
              m.content ? (
                <Markdown pending={m.pending}>{m.content}</Markdown>
              ) : m.pending ? (
                <span className="cursor">▍</span>
              ) : null
            ) : (
              m.content
            )}
            {m.audioUrl ? (
              <button
                className="replay"
                onClick={() => void audioPlayer.play(m.audioUrl!)}
                title="Ouvir novamente"
              >
                🔊 Ouvir
              </button>
            ) : null}
            {m.sources && m.sources.length > 0 ? (
              <Sources sources={m.sources} />
            ) : null}
          </div>
        </div>
      ))}
      <div ref={endRef} />

      {zoom ? (
        <div
          className="lightbox"
          onClick={() => setZoom(null)}
          role="dialog"
          aria-label="Imagem ampliada"
        >
          <button
            className="lightbox__close"
            onClick={() => setZoom(null)}
            title="Fechar (Esc)"
            aria-label="Fechar"
          >
            ✕
          </button>
          <img
            className="lightbox__img"
            src={zoom}
            alt="imagem ampliada"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      ) : null}
    </div>
  );
}
