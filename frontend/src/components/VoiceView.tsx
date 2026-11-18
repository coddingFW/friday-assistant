// Modo mãos-livres: tela dedicada à conversa por voz. Mostra o estado da Friday
// (indicador abstrato ou avatar, conforme a preferência), o texto em destaque do
// momento e a transcrição da conversa ao lado.

import { useEffect, useRef } from "react";
import type { ChatMessage, StatusState } from "../types";
import { FriendlyAvatar } from "./FriendlyAvatar";
import { Icon } from "./Icon";

interface VoiceViewProps {
  status: StatusState;
  messages: ChatMessage[];
  requireWakeWord: boolean;
  wakeWord: string;
  muted: boolean;
  onToggleMuted: (v: boolean) => void;
  speaking: boolean;
  onStopSpeaking: () => void;
  onExit: () => void;
  showAvatar: boolean;
}

/** Texto falável: tira blocos de código e marcação para a legenda. */
function plain(text: string): string {
  return text
    .replace(/```[\s\S]*?(```|$)/g, " [código] ")
    .replace(/[*_`#>]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function tail(text: string, max = 220): string {
  return text.length > max ? `…${text.slice(text.length - max).replace(/^\S*\s/, "")}` : text;
}

export function VoiceView(p: VoiceViewProps) {
  const lastUser = [...p.messages].reverse().find((m) => m.role === "user");
  const lastAi = p.messages[p.messages.length - 1]?.role === "assistant" ? p.messages[p.messages.length - 1] : undefined;
  const working = p.status === "thinking" || p.status === "searching";
  const answering = p.status === "responding" || p.speaking;

  const label = answering
    ? "Respondendo"
    : p.status === "searching"
      ? "Buscando"
      : working
        ? "Pensando"
        : p.requireWakeWord
          ? `Diga “${p.wakeWord}”`
          : "Ouvindo";

  const caption =
    answering && lastAi?.content
      ? tail(plain(lastAi.content))
      : working && lastUser
        ? lastUser.content
        : p.requireWakeWord
          ? `Chame “${p.wakeWord}” e faça a sua pergunta.`
          : "Pode falar — estou ouvindo.";
  const captionDim = !answering && !working;

  const logRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [p.messages]);

  const phase = answering ? "answering" : working ? "working" : "listening";

  return (
    <div className="voice">
      <main className="voice__main">
        <header className="voice__top">
          <div className="brand">
            <span className="brand__mark" aria-hidden="true">
              <Icon name="plus" size={12} strokeWidth={3} />
            </span>
            <span className="brand__name">Friday</span>
          </div>
          <span className="pill">
            <span className="dot dot--accent" />
            Mãos-livres{p.requireWakeWord ? ` · palavra “${p.wakeWord}”` : ""}
          </span>
        </header>

        <div className="voice__stage" aria-live="polite">
          {p.showAvatar ? (
            <FriendlyAvatar status={p.status} />
          ) : (
            <div className={`orb orb--${phase}`} aria-hidden="true">
              <span className="orb__ring orb__ring--outer" />
              <span className="orb__ring" />
              <span className="orb__core">
                <Icon name={answering ? "volume" : "mic"} size={28} />
              </span>
            </div>
          )}
          <span className="voice__label">{label}</span>
          <p className={`voice__caption ${captionDim ? "is-dim" : ""}`}>{caption}</p>
          <div className={`bars ${phase !== "working" ? "is-live" : ""}`} aria-hidden="true">
            {Array.from({ length: 15 }, (_, i) => (
              <span key={i} style={{ animationDelay: `${(i % 5) * 90}ms` }} />
            ))}
          </div>
        </div>

        <div className="voice__controls">
          <button
            type="button"
            className="round-btn"
            onClick={() => p.onToggleMuted(!p.muted)}
            aria-pressed={p.muted}
            aria-label={p.muted ? "Ligar a voz da Friday" : "Silenciar a voz da Friday"}
            title={p.muted ? "Ligar a voz da Friday" : "Silenciar a voz da Friday"}
          >
            <Icon name={p.muted ? "volumeOff" : "volume"} size={20} />
          </button>
          {p.speaking ? (
            <button type="button" className="round-btn" onClick={p.onStopSpeaking} aria-label="Interromper a fala" title="Interromper a fala">
              <Icon name="stop" size={18} />
            </button>
          ) : null}
          <button type="button" className="btn btn--lg" onClick={p.onExit}>
            <Icon name="keyboard" size={18} />
            Voltar ao chat
          </button>
        </div>
      </main>

      <aside className="voice__log" aria-label="Transcrição">
        <div className="voice__log-head">
          <h2>Transcrição</h2>
        </div>
        <div className="voice__log-body" ref={logRef}>
          {p.messages.length === 0 ? (
            <p className="side-empty">O que for dito aparece aqui.</p>
          ) : (
            p.messages.map((m) => (
              <div key={m.id} className={`turn turn--${m.role}`}>
                <span className="turn__who">{m.role === "user" ? "Você" : "Friday"}</span>
                <p>{m.content ? tail(plain(m.content), 400) : m.pending ? "…" : ""}</p>
              </div>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}
