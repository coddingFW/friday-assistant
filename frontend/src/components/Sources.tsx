import type { Source } from "../types";

export function Sources({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;
  return (
    <div className="sources">
      <span className="sources__label">Fontes</span>
      <ol className="sources__list">
        {sources.map((s, i) => (
          <li key={i}>
            <a href={s.url} target="_blank" rel="noreferrer noopener">
              {s.title || s.url}
            </a>
          </li>
        ))}
      </ol>
    </div>
  );
}
