// Renderiza markdown das respostas: parágrafos, listas, links, negrito e blocos
// de código com destaque de sintaxe (highlight.js via rehype) e botão "Copiar".
// Blocos renderáveis (HTML/SVG) — ex.: um mockup gerado pela Friday — ganham um
// toggle "Visualização/Código" que renderiza o resultado ao vivo (CodePreview).

import { createContext, useContext, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { CodePreview } from "./CodePreview";

/* eslint-disable @typescript-eslint/no-explicit-any */

// Enquanto a resposta ainda está chegando (streaming), NÃO renderiza a prévia:
// o HTML está incompleto. Mostra o código crescendo e revela o resultado no fim.
const StreamingContext = createContext(false);

//: Linguagens que sabemos pré-visualizar.
const PREVIEWABLE = new Set(["html", "htm", "svg"]);

/** Reconstrói o texto puro de um nó do React (as folhas são strings). */
function extractText(node: any): string {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (typeof node === "object" && node.props) return extractText(node.props.children);
  return "";
}

function CodeBlock(props: any) {
  const { children, node, ...rest } = props;
  const ref = useRef<HTMLPreElement>(null);
  const [copied, setCopied] = useState(false);
  const streaming = useContext(StreamingContext);

  const child = Array.isArray(children) ? children[0] : children;
  const className: string = child?.props?.className ?? "";
  const lang = /language-([\w-]+)/.exec(className)?.[1] ?? "código";

  const previewable = PREVIEWABLE.has(lang);
  const code = useMemo(
    () => (previewable ? extractText(child?.props?.children) : ""),
    [previewable, child],
  );
  // Prévia como padrão para blocos renderáveis (revela o mockup prontamente);
  // durante o streaming, força "código" (o HTML ainda está incompleto).
  const [showPreview, setShowPreview] = useState(true);
  const preview = previewable && showPreview && !streaming;

  const copy = () => {
    const text = ref.current?.textContent ?? code;
    navigator.clipboard?.writeText(text).catch(() => undefined);
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  return (
    <div className="md-code">
      <div className="md-code__bar">
        <span className="md-code__lang">{preview ? "visualização" : lang}</span>
        <div className="md-code__actions">
          {previewable && !streaming ? (
            <button
              type="button"
              className="md-code__toggle"
              onClick={() => setShowPreview((v) => !v)}
              title={showPreview ? "Ver o código" : "Ver a visualização"}
            >
              {showPreview ? "⟨⟩ Código" : "▶ Visualização"}
            </button>
          ) : null}
          <button type="button" className="md-code__copy" onClick={copy}>
            {copied ? "Copiado!" : "Copiar"}
          </button>
        </div>
      </div>
      {preview ? (
        <CodePreview code={code} lang={lang} />
      ) : (
        <pre ref={ref} {...rest}>
          {children}
        </pre>
      )}
    </div>
  );
}

function Anchor(props: any) {
  const { node, ...rest } = props;
  return <a {...rest} target="_blank" rel="noopener noreferrer" />;
}

export function Markdown({
  children,
  pending = false,
}: {
  children: string;
  pending?: boolean;
}) {
  return (
    <StreamingContext.Provider value={pending}>
      <div className="md">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
          components={{ pre: CodeBlock, a: Anchor }}
        >
          {children}
        </ReactMarkdown>
      </div>
    </StreamingContext.Provider>
  );
}
