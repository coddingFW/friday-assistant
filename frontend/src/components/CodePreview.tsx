// Pré-visualização ao vivo de um bloco de código renderável (HTML/SVG) — ex.:
// um mockup que a Friday gerou. Renderiza dentro de um <iframe sandbox> isolado:
// com "allow-scripts" mas SEM "allow-same-origin", o conteúdo roda numa origem
// opaca e não enxerga o app (DOM, storage, cookies) nem o backend local.
//
// Controles: largura (desktop/mobile, útil p/ conferir responsividade do mockup)
// e tela cheia. O quadro é redimensionável na vertical (CSS resize).

import { useEffect, useMemo, useState } from "react";

interface CodePreviewProps {
  code: string;
  /** "html" | "svg" (usado para decidir como embrulhar o conteúdo). */
  lang: string;
}

/** Embrulha o código num documento HTML completo, pronto para o srcdoc. */
function toDocument(code: string, lang: string): string {
  const src = code.trim();
  const isSvg = lang === "svg" || src.toLowerCase().startsWith("<svg");
  if (isSvg) {
    return `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;height:100%}body{display:grid;place-items:center;background:#fff}svg{max-width:100%;height:auto}</style>
</head><body>${src}</body></html>`;
  }
  // Documento completo: usa como veio (preserva o <head>/estilos do mockup).
  if (/<!doctype/i.test(src) || /<html[\s>]/i.test(src)) return src;
  // Fragmento: embrulha com uma base neutra e agradável.
  return `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{margin:0;padding:16px;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#fff;color:#111;line-height:1.5}</style>
</head><body>${src}</body></html>`;
}

type Device = "full" | "mobile";

export function CodePreview({ code, lang }: CodePreviewProps) {
  const doc = useMemo(() => toDocument(code, lang), [code, lang]);
  const [device, setDevice] = useState<Device>("full");
  const [full, setFull] = useState(false);

  useEffect(() => {
    if (!full) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setFull(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [full]);

  const frame = (fullscreen: boolean) => (
    <div className={`cpv__stage ${device === "mobile" ? "cpv__stage--mobile" : ""}`}>
      <iframe
        className="cpv__frame"
        title="Pré-visualização"
        srcDoc={doc}
        sandbox="allow-scripts"
        loading="lazy"
        style={fullscreen ? { height: "100%" } : undefined}
      />
    </div>
  );

  return (
    <div className="cpv">
      <div className="cpv__bar">
        <div className="cpv__seg" role="group" aria-label="Largura da visualização">
          <button
            className={`cpv__segbtn ${device === "full" ? "cpv__segbtn--on" : ""}`}
            onClick={() => setDevice("full")}
            title="Largura total"
            aria-pressed={device === "full"}
          >
            🖥
          </button>
          <button
            className={`cpv__segbtn ${device === "mobile" ? "cpv__segbtn--on" : ""}`}
            onClick={() => setDevice("mobile")}
            title="Largura de celular"
            aria-pressed={device === "mobile"}
          >
            📱
          </button>
        </div>
        <button
          className="cpv__expand"
          onClick={() => setFull(true)}
          title="Abrir em tela cheia"
        >
          ⤢ Tela cheia
        </button>
      </div>

      <div className="cpv__wrap">{frame(false)}</div>

      {full ? (
        <div
          className="cpv__overlay"
          role="dialog"
          aria-label="Pré-visualização em tela cheia"
          onClick={() => setFull(false)}
        >
          <div className="cpv__overlaybox" onClick={(e) => e.stopPropagation()}>
            <div className="cpv__bar cpv__bar--over">
              <div className="cpv__seg" role="group" aria-label="Largura">
                <button
                  className={`cpv__segbtn ${device === "full" ? "cpv__segbtn--on" : ""}`}
                  onClick={() => setDevice("full")}
                  title="Largura total"
                >
                  🖥
                </button>
                <button
                  className={`cpv__segbtn ${device === "mobile" ? "cpv__segbtn--on" : ""}`}
                  onClick={() => setDevice("mobile")}
                  title="Largura de celular"
                >
                  📱
                </button>
              </div>
              <button
                className="cpv__expand"
                onClick={() => setFull(false)}
                title="Fechar (Esc)"
              >
                ✕ Fechar
              </button>
            </div>
            <div className="cpv__overlaystage">{frame(true)}</div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
