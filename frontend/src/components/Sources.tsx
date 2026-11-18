import type { Source } from "../types";

function host(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function Sources({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;
  return (
    <div className="sources" aria-label="Fontes">
      {sources.map((s, i) => (
        <a key={i} className="source" href={s.url} target="_blank" rel="noreferrer noopener" title={s.title || s.url}>
          <span className="source__n">{i + 1}</span>
          <span className="source__host">{host(s.url)}</span>
        </a>
      ))}
    </div>
  );
}
