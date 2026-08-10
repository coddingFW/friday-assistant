import type { Source } from "../types";

export function Sources({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;
  return (
    <div className="sources">
      <span className="sources__label">Fontes</span>
      <div className="sources__chips">
        {sources.map((s, i) => (
          <a
            key={i}
            className="chip"
            href={s.url}
            target="_blank"
            rel="noreferrer noopener"
            title={s.url}
          >
            <span className="chip__i" aria-hidden="true">◆</span>
            {s.title || s.url}
          </a>
        ))}
      </div>
    </div>
  );
}
