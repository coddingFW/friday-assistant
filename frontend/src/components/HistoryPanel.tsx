// Painel de histórico de conversas (memória de longo prazo — Fase 9). Lista as
// conversas persistidas, permite começar uma nova, retomar uma existente e
// apagar (com confirmação inline). A conversa ativa fica destacada.

import { useState } from "react";
import type { ConversationSummary } from "../types";

/** Formata um timestamp ISO como tempo relativo curto, em pt-BR. */
function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const secs = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (secs < 45) return "agora";
  const mins = Math.round(secs / 60);
  if (mins < 60) return `há ${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `há ${hours} h`;
  const days = Math.round(hours / 24);
  if (days === 1) return "ontem";
  if (days < 7) return `há ${days} dias`;
  return new Date(then).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
  });
}

interface HistoryPanelProps {
  items: ConversationSummary[];
  activeId: string | null;
  loading: boolean;
  error: string | null;
  onNew: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onRefresh: () => void;
  onClose: () => void;
}

export function HistoryPanel({
  items,
  activeId,
  loading,
  error,
  onNew,
  onSelect,
  onDelete,
  onRefresh,
  onClose,
}: HistoryPanelProps) {
  // Id da conversa aguardando confirmação de exclusão (confirmação inline).
  const [confirming, setConfirming] = useState<string | null>(null);

  return (
    <aside className="hist">
      <div className="hist__head">
        <span className="hist__title">Histórico</span>
        <div className="hist__actions">
          <button
            className="hist__icon"
            onClick={onRefresh}
            title="Recarregar"
            aria-label="Recarregar o histórico"
            disabled={loading}
          >
            ⟳
          </button>
          <button
            className="hist__icon"
            onClick={onClose}
            title="Fechar o painel"
            aria-label="Fechar o painel"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="hist__new">
        <button className="hist__newbtn" onClick={onNew}>
          ＋ Nova conversa
        </button>
      </div>

      {error ? <p className="hist__error">{error}</p> : null}

      <div className="hist__list">
        {items.length === 0 && !loading ? (
          <p className="hist__empty">
            Nenhuma conversa ainda. O que você conversar com a Friday fica salvo
            aqui.
          </p>
        ) : (
          items.map((c) => {
            const active = c.id === activeId;
            const asking = confirming === c.id;
            return (
              <div
                key={c.id}
                className={`hist-row ${active ? "hist-row--on" : ""}`}
                onClick={() => onSelect(c.id)}
                title={c.title}
              >
                <div className="hist-row__body">
                  <span className="hist-row__title">{c.title}</span>
                  <span className="hist-row__meta">
                    {relativeTime(c.updated_at)} · {c.message_count}{" "}
                    {c.message_count === 1 ? "msg" : "msgs"}
                  </span>
                </div>
                {asking ? (
                  <div className="hist-row__confirm" onClick={(e) => e.stopPropagation()}>
                    <button
                      className="hist-row__yes"
                      onClick={() => {
                        onDelete(c.id);
                        setConfirming(null);
                      }}
                    >
                      apagar
                    </button>
                    <button
                      className="hist-row__no"
                      onClick={() => setConfirming(null)}
                    >
                      não
                    </button>
                  </div>
                ) : (
                  <button
                    className="hist-row__del"
                    title="Apagar conversa"
                    aria-label="Apagar conversa"
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirming(c.id);
                    }}
                  >
                    🗑
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
