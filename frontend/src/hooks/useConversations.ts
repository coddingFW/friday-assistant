// Hook do histórico de conversas (memória de longo prazo — Fase 9). Lista as
// conversas persistidas, permite recarregar e apagar. O REST é a fonte da
// verdade; a lista é recarregada quando a conversa ativa muda (uma nova é
// criada, ou o título/contagem de uma existente é atualizado após um turno).

import { useCallback, useEffect, useRef, useState } from "react";
import { deleteConversation, listConversations } from "../services/api";
import type { ConversationSummary } from "../types";

export interface UseConversations {
  items: ConversationSummary[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
  remove: (id: string) => Promise<void>;
}

/**
 * @param activeId conversa ativa no chat; mudanças disparam um refresh da lista
 *                 (captura a criação de uma conversa nova e a atualização de
 *                 título/contagem após o primeiro turno).
 */
export function useConversations(activeId: string | null): UseConversations {
  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) return; // evita chamadas concorrentes
    inFlight.current = true;
    setLoading(true);
    setError(null);
    try {
      setItems(await listConversations());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao carregar o histórico.");
    } finally {
      setLoading(false);
      inFlight.current = false;
    }
  }, []);

  const remove = useCallback(
    async (id: string) => {
      try {
        await deleteConversation(id);
        setItems((prev) => prev.filter((c) => c.id !== id));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Falha ao apagar a conversa.");
        throw e;
      }
    },
    [],
  );

  // Recarrega ao montar e sempre que a conversa ativa mudar.
  useEffect(() => {
    void refresh();
  }, [refresh, activeId]);

  // `refresh` é o próprio useCallback (identidade estável) — pode entrar em
  // dependências de efeitos sem recriá-los a cada render.
  return { items, loading, error, refresh, remove };
}
