import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../types";
import { audioPlayer } from "../services/audioPlayer";
import { Sources } from "./Sources";
import { Markdown } from "./Markdown";
import { Icon } from "./Icon";

interface MessageListProps {
  messages: ChatMessage[];
  codeMode: boolean;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="icon-btn icon-btn--sm"
      onClick={() => {
        navigator.clipboard?.writeText(text).catch(() => undefined);
        setCopied(true);
        setTimeout(() => setCopied(false), 1400);
      }}
      aria-label={copied ? "Copiado" : "Copiar resposta"}
      title={copied ? "Copiado" : "Copiar resposta"}
    >
      <Icon name={copied ? "check" : "copy"} size={15} />
    </button>
  );
}

export function MessageList({ messages, codeMode }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState<string | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

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
      <div className="welcome">
        <h2 className="welcome__title">Como posso ajudar?</h2>
        <ul className="welcome__list">
          <li>
            <Icon name="globe" size={16} />
            <span>Pergunte qualquer coisa — eu busco na web quando ajuda.</span>
          </li>
          <li>
            <Icon name="folder" size={16} />
            <span>
              {codeMode
                ? "Os arquivos marcados entram no contexto do modelo de código."
                : "Abra um projeto e marque arquivos para falar sobre o seu código."}
            </span>
          </li>
          <li>
            <Icon name="mic" size={16} />
            <span>Fale pelo microfone ou ligue o modo mãos-livres.</span>
          </li>
        </ul>
      </div>
    );
  }

  return (
    <div className="thread">
      {messages.map((m) =>
        m.role === "user" ? (
          <div key={m.id} className="msg-user">
            {m.image ? (
              <button type="button" className="msg-image" onClick={() => setZoom(m.image!)} aria-label="Ampliar imagem">
                <img src={m.image} alt="Imagem enviada" />
              </button>
            ) : null}
            {m.content ? <p className="msg-user__bubble">{m.content}</p> : null}
          </div>
        ) : (
          <article key={m.id} className="msg-ai">
            <div className="msg-ai__head">
              <span className="brand__mark brand__mark--sm" aria-hidden="true" />
              <span className="msg-ai__name">Friday</span>
            </div>
            <div className="msg-ai__body">
              {m.content ? (
                <Markdown pending={m.pending}>{m.content}</Markdown>
              ) : m.pending ? (
                <span className="typing" aria-label="Gerando resposta">
                  <span />
                  <span />
                  <span />
                </span>
              ) : null}
            </div>
            {m.sources && m.sources.length > 0 ? <Sources sources={m.sources} /> : null}
            {!m.pending && m.content ? (
              <div className="msg-ai__actions">
                {m.audioUrl ? (
                  <button
                    type="button"
                    className="icon-btn icon-btn--sm"
                    onClick={() => void audioPlayer.play(m.audioUrl!)}
                    aria-label="Ouvir resposta"
                    title="Ouvir"
                  >
                    <Icon name="volume" size={15} />
                  </button>
                ) : null}
                <CopyButton text={m.content} />
              </div>
            ) : null}
          </article>
        ),
      )}
      <div ref={endRef} />

      {zoom ? (
        <div className="lightbox" onClick={() => setZoom(null)} role="dialog" aria-label="Imagem ampliada">
          <button type="button" className="lightbox__close" onClick={() => setZoom(null)} aria-label="Fechar">
            <Icon name="x" />
          </button>
          <img className="lightbox__img" src={zoom} alt="Imagem ampliada" onClick={(e) => e.stopPropagation()} />
        </div>
      ) : null}
    </div>
  );
}
