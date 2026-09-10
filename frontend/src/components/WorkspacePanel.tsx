// Painel do projeto local (Fase 10). Aponta uma pasta, mostra a árvore de
// arquivos e deixa marcar quais entram no contexto da Friday (turno de código).

import { useMemo, useState } from "react";
import type { WsTreeEntry } from "../types";

interface TreeNode {
  entry: WsTreeEntry;
  children: TreeNode[];
}

/** Monta a árvore aninhada a partir da lista plana de entradas. */
function buildTree(entries: WsTreeEntry[]): TreeNode[] {
  const nodes = new Map<string, TreeNode>();
  for (const entry of entries) nodes.set(entry.path, { entry, children: [] });
  const roots: TreeNode[] = [];
  for (const node of nodes.values()) {
    const slash = node.entry.path.lastIndexOf("/");
    const parent = slash >= 0 ? nodes.get(node.entry.path.slice(0, slash)) : undefined;
    if (parent) parent.children.push(node);
    else roots.push(node);
  }
  const sort = (list: TreeNode[]) => {
    list.sort((a, b) => {
      if (a.entry.is_dir !== b.entry.is_dir) return a.entry.is_dir ? -1 : 1;
      return a.entry.name.localeCompare(b.entry.name);
    });
    list.forEach((n) => sort(n.children));
  };
  sort(roots);
  return roots;
}

/** Todos os diretórios ancestrais de um caminho (para auto-expandir). */
function ancestors(path: string): string[] {
  const parts = path.split("/");
  const acc: string[] = [];
  for (let i = 1; i < parts.length; i++) acc.push(parts.slice(0, i).join("/"));
  return acc;
}

interface WorkspacePanelProps {
  root: string | null;
  entries: WsTreeEntry[];
  selected: string[];
  loading: boolean;
  error: string | null;
  onOpen: (path: string) => void;
  onToggleSelect: (path: string) => void;
  onClearSelected: () => void;
  onClose: () => void;
}

export function WorkspacePanel({
  root,
  entries,
  selected,
  loading,
  error,
  onOpen,
  onToggleSelect,
  onClearSelected,
  onClose,
}: WorkspacePanelProps) {
  const [path, setPath] = useState(root ?? "");
  const tree = useMemo(() => buildTree(entries), [entries]);
  const selectedSet = useMemo(() => new Set(selected), [selected]);
  const [expanded, setExpanded] = useState<Set<string>>(() => {
    const s = new Set<string>();
    for (const p of selected) for (const a of ancestors(p)) s.add(a);
    return s;
  });

  const toggleExpand = (p: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(p) ? next.delete(p) : next.add(p);
      return next;
    });

  const submit = () => {
    if (path.trim()) onOpen(path);
  };

  const renderNodes = (list: TreeNode[], depth: number): JSX.Element[] =>
    list.flatMap((node) => {
      const { entry } = node;
      const pad = 8 + depth * 14;
      if (entry.is_dir) {
        const open = expanded.has(entry.path);
        return [
          <div
            key={entry.path}
            className="ws-row ws-row--dir"
            style={{ paddingLeft: pad }}
            onClick={() => toggleExpand(entry.path)}
          >
            <span className="ws-caret">{open ? "▾" : "▸"}</span>
            <span className="ws-ico">{open ? "📂" : "📁"}</span>
            <span className="ws-name">{entry.name}</span>
          </div>,
          ...(open ? renderNodes(node.children, depth + 1) : []),
        ];
      }
      const checked = selectedSet.has(entry.path);
      return [
        <div
          key={entry.path}
          className={`ws-row ws-row--file ${checked ? "ws-row--on" : ""}`}
          style={{ paddingLeft: pad }}
          onClick={() => onToggleSelect(entry.path)}
          title={entry.path}
        >
          <span className={`ws-check ${checked ? "ws-check--on" : ""}`}>
            {checked ? "✓" : ""}
          </span>
          <span className="ws-ico">📄</span>
          <span className="ws-name">{entry.name}</span>
        </div>,
      ];
    });

  return (
    <aside className="ws">
      <div className="ws__head">
        <span className="ws__title">Projeto</span>
        <button
          className="ws__x"
          onClick={onClose}
          title="Fechar o painel"
          aria-label="Fechar o painel"
        >
          ✕
        </button>
      </div>

      <div className="ws__root">
        <label className="ws__label">Pasta</label>
        <div className="ws__rootrow">
          <input
            className="ws__input"
            type="text"
            value={path}
            placeholder="C:\caminho\do\projeto"
            onChange={(e) => setPath(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") submit();
            }}
            spellCheck={false}
          />
          <button className="ws__open" onClick={submit} disabled={loading}>
            {loading ? "…" : "Abrir"}
          </button>
        </div>
        {error ? <p className="ws__error">{error}</p> : null}
      </div>

      {selected.length > 0 ? (
        <div className="ws__ctx">
          <span>
            {selected.length} {selected.length === 1 ? "arquivo" : "arquivos"} no
            contexto
          </span>
          <button className="ws__ctxclear" onClick={onClearSelected}>
            limpar
          </button>
        </div>
      ) : null}

      <div className="ws__tree">
        {!root ? (
          <p className="ws__empty">
            Aponte uma pasta para a Friday ler seu projeto e te ajudar a programar.
          </p>
        ) : entries.length === 0 && !loading ? (
          <p className="ws__empty">Nenhum arquivo encontrado.</p>
        ) : (
          renderNodes(tree, 0)
        )}
      </div>
    </aside>
  );
}
