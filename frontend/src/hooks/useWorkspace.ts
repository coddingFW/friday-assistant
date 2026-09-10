// Hook do workspace (projeto local — Fase 10). Gerencia a raiz aberta, a árvore
// de arquivos e a seleção de "arquivos no contexto". A raiz e a seleção são
// persistidas em localStorage e restauradas ao abrir o app.

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getWorkspaceRoot,
  getWorkspaceTree,
  setWorkspaceRoot,
} from "../services/api";
import type { WsTreeEntry } from "../types";

const ROOT_KEY = "friday.ws.root";
const SEL_KEY = "friday.ws.selected";

const readList = (key: string): string[] => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
};
const writeJson = (key: string, value: unknown): void => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* opcional */
  }
};

export interface UseWorkspace {
  root: string | null;
  entries: WsTreeEntry[];
  selected: string[];
  loading: boolean;
  error: string | null;
  openRoot: (path: string) => void;
  refresh: () => void;
  toggleSelect: (path: string) => void;
  clearSelected: () => void;
}

export function useWorkspace(): UseWorkspace {
  const [root, setRoot] = useState<string | null>(null);
  const [entries, setEntries] = useState<WsTreeEntry[]>([]);
  const [selected, setSelected] = useState<string[]>(() => readList(SEL_KEY));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const restored = useRef(false);

  const loadTree = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEntries(await getWorkspaceTree());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao listar o projeto.");
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const openRoot = useCallback(
    (path: string) => {
      const clean = path.trim();
      if (!clean) return;
      setLoading(true);
      setError(null);
      void (async () => {
        try {
          const { root: newRoot } = await setWorkspaceRoot(clean);
          setRoot(newRoot);
          writeJson(ROOT_KEY, newRoot);
          // Troca de projeto zera a seleção (caminhos antigos não valem mais).
          setSelected([]);
          writeJson(SEL_KEY, []);
          await loadTree();
        } catch (e) {
          setError(e instanceof Error ? e.message : "Não foi possível abrir a pasta.");
          setLoading(false);
        }
      })();
    },
    [loadTree],
  );

  // Restaura a raiz ao montar: usa a do backend ou reabre a salva localmente.
  useEffect(() => {
    if (restored.current) return;
    restored.current = true;
    void (async () => {
      try {
        const { root: current } = await getWorkspaceRoot();
        if (current) {
          setRoot(current);
          writeJson(ROOT_KEY, current);
          await loadTree();
          return;
        }
      } catch {
        /* workspace pode estar desativado; segue sem projeto */
      }
      const saved = localStorage.getItem(ROOT_KEY);
      if (saved) openRoot(saved);
    })();
  }, [loadTree, openRoot]);

  const toggleSelect = useCallback((path: string) => {
    setSelected((prev) => {
      const next = prev.includes(path)
        ? prev.filter((p) => p !== path)
        : [...prev, path];
      writeJson(SEL_KEY, next);
      return next;
    });
  }, []);

  const clearSelected = useCallback(() => {
    setSelected([]);
    writeJson(SEL_KEY, []);
  }, []);

  return {
    root,
    entries,
    selected,
    loading,
    error,
    openRoot,
    refresh: () => void loadTree(),
    toggleSelect,
    clearSelected,
  };
}
