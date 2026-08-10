// Renderiza markdown das respostas: parágrafos, listas, links, negrito e blocos
// de código com destaque de sintaxe (highlight.js via rehype) e botão "Copiar".

import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

/* eslint-disable @typescript-eslint/no-explicit-any */

function CodeBlock(props: any) {
  const { children, node, ...rest } = props;
  const ref = useRef<HTMLPreElement>(null);
  const [copied, setCopied] = useState(false);

  const child = Array.isArray(children) ? children[0] : children;
  const className: string = child?.props?.className ?? "";
  const lang = /language-([\w-]+)/.exec(className)?.[1] ?? "código";

  const copy = () => {
    const text = ref.current?.textContent ?? "";
    navigator.clipboard?.writeText(text).catch(() => undefined);
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  return (
    <div className="md-code">
      <div className="md-code__bar">
        <span className="md-code__lang">{lang}</span>
        <button type="button" className="md-code__copy" onClick={copy}>
          {copied ? "Copiado!" : "Copiar"}
        </button>
      </div>
      <pre ref={ref} {...rest}>
        {children}
      </pre>
    </div>
  );
}

function Anchor(props: any) {
  const { node, ...rest } = props;
  return <a {...rest} target="_blank" rel="noopener noreferrer" />;
}

export function Markdown({ children }: { children: string }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
        components={{ pre: CodeBlock, a: Anchor }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
