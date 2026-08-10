import type { StatusState } from "../types";

const LABELS: Record<StatusState, string> = {
  idle: "Ocioso",
  thinking: "Pensando",
  searching: "Buscando",
  responding: "Respondendo",
  listening: "Ouvindo",
};

export function StatusIndicator({ status }: { status: StatusState }) {
  const active = status !== "idle";
  return (
    <div className={`status ${active ? "status--active" : ""}`}>
      <span className={`status__dot status__dot--${status}`} />
      {LABELS[status]}
    </div>
  );
}
