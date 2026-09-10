import type { HealthResponse, StatusState } from "../types";
import { StatusIndicator } from "./StatusIndicator";

interface HeaderProps {
  health: HealthResponse | null;
  connected: boolean;
  status: StatusState;
  codeActive: boolean;
  projectOpen: boolean;
  onToggleProject: () => void;
  historyOpen: boolean;
  onToggleHistory: () => void;
  onCustomize: () => void;
}

export function Header({
  health,
  connected,
  status,
  codeActive,
  projectOpen,
  onToggleProject,
  historyOpen,
  onToggleHistory,
  onCustomize,
}: HeaderProps) {
  return (
    <header className="header">
      <div className="header__brand">
        <span className="header__logo">◆</span>
        <div>
          <h1 className="header__title">Friday</h1>
          <p className="header__subtitle">
            {codeActive ? (
              <span className="header__code">modo código</span>
            ) : health ? (
              `${health.llm_model}`
            ) : (
              "conectando…"
            )}
            {health && !health.llm_reachable ? " · LLM offline" : ""}
          </p>
        </div>
      </div>
      <div className="header__right">
        <button
          type="button"
          className={`header__btn ${historyOpen ? "header__btn--on" : ""}`}
          onClick={onToggleHistory}
          title="Histórico de conversas"
          aria-pressed={historyOpen}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 3v5h5" />
            <path d="M3.05 13A9 9 0 1 0 6 5.3L3 8" />
            <path d="M12 7v5l3 2" />
          </svg>
          Histórico
        </button>
        <button
          type="button"
          className={`header__btn ${projectOpen ? "header__btn--on" : ""}`}
          onClick={onToggleProject}
          title="Projeto local"
          aria-pressed={projectOpen}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          </svg>
          Projeto
        </button>
        <button
          type="button"
          className="header__customize"
          onClick={onCustomize}
          title="Personalizar avatar"
          aria-label="Personalizar avatar"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <circle cx="13.5" cy="6.5" r="2.5" /><circle cx="6.5" cy="12" r="2.5" />
            <circle cx="17" cy="14" r="2.5" /><path d="M12 22a10 10 0 1 1 10-10c0 2-2 3-4 3h-1a2 2 0 0 0-1 3.5A2 2 0 0 1 12 22z" />
          </svg>
        </button>
        <StatusIndicator status={status} />
        <span className={`conn ${connected ? "conn--on" : "conn--off"}`}>
          {connected ? "online" : "offline"}
        </span>
      </div>
    </header>
  );
}
