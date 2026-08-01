import type { HealthResponse, StatusState } from "../types";
import { StatusIndicator } from "./StatusIndicator";

interface HeaderProps {
  health: HealthResponse | null;
  connected: boolean;
  status: StatusState;
}

export function Header({ health, connected, status }: HeaderProps) {
  return (
    <header className="header">
      <div className="header__brand">
        <span className="header__logo">◆</span>
        <div>
          <h1 className="header__title">Friday</h1>
          <p className="header__subtitle">
            {health ? `${health.llm_model}` : "conectando…"}
            {health && !health.llm_reachable ? " · LLM offline" : ""}
          </p>
        </div>
      </div>
      <div className="header__right">
        <StatusIndicator status={status} />
        <span className={`conn ${connected ? "conn--on" : "conn--off"}`}>
          {connected ? "online" : "offline"}
        </span>
      </div>
    </header>
  );
}
