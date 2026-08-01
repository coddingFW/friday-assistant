import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";
import { Sources } from "./Sources";

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
            {m.content || (m.pending ? <span className="cursor">▍</span> : "")}
            {m.pending && m.content ? <span className="cursor">▍</span> : null}
            {m.sources && m.sources.length > 0 ? (
              <Sources sources={m.sources} />
            ) : null}
          </div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
