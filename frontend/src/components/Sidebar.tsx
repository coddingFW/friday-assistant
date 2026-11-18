// Barra lateral: marca + nova conversa, busca, projeto local (árvore com seleção
// de arquivos para o contexto) e conversas recentes (retomar/apagar).

import { useEffect, useMemo, useState } from "react";
import type { ConversationSummary, WsTreeEntry } from "../types";
import { FileEditor } from "./FileEditor";
import { Icon } from "./Icon";

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

/** Formata um timestamp ISO como tempo relativo curto, em pt-BR. */
function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const secs = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (secs < 45) return "agora";
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h`;
  const days = Math.round(hours / 24);
  if (days === 1) return "ontem";
  if (days < 7) return `${days} d`;
  return new Date(then).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

function baseName(path: string): string {
  const parts = path.replace(/[\\/]+$/, "").split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  // Conversas
  conversations: ConversationSummary[];
  activeId: string | null;
  conversationsError: string | null;
  onNew: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  // Projeto
  root: string | null;
  entries: WsTreeEntry[];
  selected: string[];
  wsLoading: boolean;
  wsError: string | null;
  onOpenRoot: (path: string) => void;
  onToggleSelect: (path: string) => void;
  onFileSaved?: () => void;
  // Rodapé
  llmReachable: boolean | null;
  onCustomize: () => void;
}

export function Sidebar(props: SidebarProps) {
  const {
    open,
    onClose,
    conversations,
    activeId,
    conversationsError,
    onNew,
    onSelect,
    onDelete,
    root,
    entries,
    selected,
    wsLoading,
    wsError,
    onOpenRoot,
    onToggleSelect,
    onFileSaved,
    llmReachable,
    onCustomize,
  } = props;

  const [query, setQuery] = useState("");
  const [rootInput, setRootInput] = useState(root ?? "");
  const [editingRoot, setEditingRoot] = useState(!root);
  const [editingFile, setEditingFile] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);
  // A raiz chega assíncrona (GET no carregamento): sincroniza o formulário.
  useEffect(() => {
    setRootInput(root ?? "");
    setEditingRoot(!root);
  }, [root]);
  const tree = useMemo(() => buildTree(entries), [entries]);
  const selectedSet = useMemo(() => new Set(selected), [selected]);
  const [expanded, setExpanded] = useState<Set<string>>(() => {
    const s = new Set<string>();
    for (const p of selected) for (const a of ancestors(p)) s.add(a);
    return s;
  });

  const q = query.trim().toLowerCase();
  const filteredConversations = q
    ? conversations.filter((c) => c.title.toLowerCase().includes(q))
    : conversations;
  const matchingFiles = q
    ? entries.filter((e) => !e.is_dir && e.path.toLowerCase().includes(q)).slice(0, 50)
    : [];

  const toggleExpand = (p: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(p)) next.delete(p);
      else next.add(p);
      return next;
    });

  const submitRoot = () => {
    if (!rootInput.trim()) return;
    onOpenRoot(rootInput.trim());
    setEditingRoot(false);
  };

  const fileRow = (entry: WsTreeEntry, pad: number, label: string) => {
    const checked = selectedSet.has(entry.path);
    return (
      <div key={entry.path} className={`tree-row ${checked ? "is-selected" : ""}`} style={{ paddingLeft: pad }}>
        <button
          type="button"
          className="tree-row__main"
          onClick={() => onToggleSelect(entry.path)}
          aria-pressed={checked}
          title={checked ? `Tirar ${entry.path} do contexto` : `Usar ${entry.path} no contexto`}
        >
          <span className="tree-row__name mono">{label}</span>
          {checked ? <span className="dot dot--accent" aria-label="no contexto" /> : null}
        </button>
        <button
          type="button"
          className="tree-row__edit"
          onClick={() => setEditingFile(entry.path)}
          aria-label={`Editar ${entry.name}`}
          title="Editar arquivo"
        >
          <Icon name="pencil" size={13} />
        </button>
      </div>
    );
  };

  const renderNodes = (list: TreeNode[], depth: number): JSX.Element[] =>
    list.flatMap((node) => {
      const { entry } = node;
      const pad = 8 + depth * 14;
      if (entry.is_dir) {
        const isOpen = expanded.has(entry.path);
        return [
          <div key={entry.path} className="tree-row tree-row--dir" style={{ paddingLeft: pad }}>
            <button
              type="button"
              className="tree-row__main"
              onClick={() => toggleExpand(entry.path)}
              aria-expanded={isOpen}
            >
              <Icon name={isOpen ? "chevronDown" : "chevronRight"} size={13} />
              <span className="tree-row__name">{entry.name}</span>
            </button>
          </div>,
          ...(isOpen ? renderNodes(node.children, depth + 1) : []),
        ];
      }
      return [fileRow(entry, pad + 19, entry.name)];
    });

  return (
    <>
      {open ? <div className="scrim" onClick={onClose} aria-hidden="true" /> : null}
      <nav className={`sidebar ${open ? "is-open" : ""}`} aria-label="Navegação">
        <div className="sidebar__brand">
          <div className="brand">
            <span className="brand__mark" aria-hidden="true">
              <Icon name="plus" size={12} strokeWidth={3} />
            </span>
            <span className="brand__name">Friday</span>
          </div>
          <button type="button" className="icon-btn icon-btn--outline" onClick={onNew} aria-label="Nova conversa" title="Nova conversa">
            <Icon name="plus" />
          </button>
        </div>

        <label className="search">
          <Icon name="search" size={14} />
          <span className="sr-only">Buscar conversas e arquivos</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar…"
            spellCheck={false}
          />
          {query ? (
            <button type="button" className="search__clear" onClick={() => setQuery("")} aria-label="Limpar busca">
              <Icon name="x" size={12} />
            </button>
          ) : null}
        </label>

        <section className="side-section side-section--project" aria-labelledby="side-project">
          <div className="side-section__head">
            <h2 id="side-project" className="eyebrow">Projeto</h2>
            {root && !editingRoot ? (
              <button type="button" className="link-btn" onClick={() => setEditingRoot(true)} title={root}>
                {baseName(root)}
                <Icon name="pencil" size={12} />
              </button>
            ) : null}
          </div>

          {editingRoot ? (
            <form
              className="root-form"
              onSubmit={(e) => {
                e.preventDefault();
                submitRoot();
              }}
            >
              <label className="sr-only" htmlFor="root-input">Pasta do projeto</label>
              <input
                id="root-input"
                className="input mono"
                value={rootInput}
                onChange={(e) => setRootInput(e.target.value)}
                placeholder="C:\caminho\do\projeto"
                spellCheck={false}
              />
              <div className="root-form__actions">
                {root ? (
                  <button type="button" className="btn btn--ghost btn--sm" onClick={() => setEditingRoot(false)}>
                    Cancelar
                  </button>
                ) : null}
                <button type="submit" className="btn btn--sm" disabled={wsLoading}>
                  {wsLoading ? "Abrindo…" : "Abrir"}
                </button>
              </div>
            </form>
          ) : null}
          {wsError ? <p className="side-error">{wsError}</p> : null}

          <div className="tree">
            {!root && !editingRoot ? null : !root ? (
              <p className="side-empty">Abra uma pasta para a Friday ler o seu código.</p>
            ) : q ? (
              matchingFiles.length ? (
                matchingFiles.map((e) => fileRow(e, 8, e.path))
              ) : (
                <p className="side-empty">Nenhum arquivo com “{query}”.</p>
              )
            ) : entries.length === 0 && !wsLoading ? (
              <p className="side-empty">Nenhum arquivo encontrado.</p>
            ) : (
              renderNodes(tree, 0)
            )}
          </div>
        </section>

        <section className="side-section side-section--recent" aria-labelledby="side-recent">
          <div className="side-section__head">
            <h2 id="side-recent" className="eyebrow">Recentes</h2>
          </div>
          {conversationsError ? <p className="side-error">{conversationsError}</p> : null}
          <div className="conv-list">
            {filteredConversations.length === 0 ? (
              <p className="side-empty">{q ? "Nenhuma conversa encontrada." : "As conversas ficam salvas aqui."}</p>
            ) : (
              filteredConversations.map((c) => {
                const active = c.id === activeId;
                const asking = confirming === c.id;
                return (
                  <div key={c.id} className={`conv ${active ? "is-active" : ""}`}>
                    {asking ? (
                      <div className="conv__confirm">
                        <span>Apagar conversa?</span>
                        <button type="button" className="btn btn--danger btn--sm" onClick={() => { onDelete(c.id); setConfirming(null); }}>
                          Apagar
                        </button>
                        <button type="button" className="btn btn--ghost btn--sm" onClick={() => setConfirming(null)}>
                          Não
                        </button>
                      </div>
                    ) : (
                      <>
                        <button type="button" className="conv__main" onClick={() => onSelect(c.id)} aria-current={active ? "page" : undefined}>
                          <span className="conv__title">{c.title}</span>
                          <span className="conv__time">{relativeTime(c.updated_at)}</span>
                        </button>
                        <button type="button" className="conv__del" onClick={() => setConfirming(c.id)} aria-label={`Apagar ${c.title}`} title="Apagar">
                          <Icon name="trash" size={13} />
                        </button>
                      </>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </section>

        <div className="sidebar__foot">
          <span className="engine">
            <span className={`dot ${llmReachable === false ? "dot--danger" : llmReachable ? "dot--ok" : ""}`} />
            {llmReachable === false ? "Ollama offline" : "Ollama · local"}
          </span>
          <button type="button" className="icon-btn" onClick={onCustomize} aria-label="Personalizar avatar" title="Personalizar avatar">
            <Icon name="palette" />
          </button>
        </div>
      </nav>

      {editingFile ? (
        <FileEditor path={editingFile} onClose={() => setEditingFile(null)} onSaved={onFileSaved} />
      ) : null}
    </>
  );
}
