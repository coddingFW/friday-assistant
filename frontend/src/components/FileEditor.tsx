// Editor de arquivo do projeto (Fase 10 — escrita). Abre um arquivo da árvore,
// permite editar e SALVAR (sempre confirmado pelo usuário). O backend confina à
// raiz e guarda um backup do conteúdo anterior antes de sobrescrever.
//
// Segurança: se a leitura veio truncada (arquivo grande), salvar apagaria o
// restante — nesse caso a edição fica desabilitada.

import { useEffect, useState } from "react";
import { getWorkspaceFile, writeWorkspaceFile } from "../services/api";
import type { WsWriteResult } from "../types";

interface FileEditorProps {
  path: string;
  onClose: () => void;
  onSaved?: () => void;
}

export function FileEditor({ path, onClose, onSaved }: FileEditorProps) {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [truncated, setTruncated] = useState(false);
  const [original, setOriginal] = useState("");
  const [text, setText] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState<WsWriteResult | null>(null);

  const dirty = text !== original;

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setLoadError(null);
    getWorkspaceFile(path)
      .then((f) => {
        if (!alive) return;
        setOriginal(f.text);
        setText(f.text);
        setTruncated(f.truncated);
      })
      .catch((e) => alive && setLoadError(e instanceof Error ? e.message : "Falha ao abrir."))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [path]);

  // Esc fecha (sem perguntar; o botão Salvar é a ação deliberada).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const doSave = () => {
    setSaving(true);
    setSaveError(null);
    void (async () => {
      try {
        const res = await writeWorkspaceFile(path, text);
        setSaved(res);
        setOriginal(text); // agora limpo
        setConfirming(false);
        onSaved?.();
      } catch (e) {
        setSaveError(e instanceof Error ? e.message : "Falha ao salvar.");
        setConfirming(false);
      } finally {
        setSaving(false);
      }
    })();
  };

  return (
    <div className="fed" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="fed__box" onClick={(e) => e.stopPropagation()}>
        <div className="fed__head">
          <span className="fed__title" title={path}>
            Editar · <span className="fed__path">{path}</span>
          </span>
          <button className="fed__x" onClick={onClose} aria-label="Fechar o editor">
            ✕
          </button>
        </div>

        {loading ? (
          <div className="fed__empty">Carregando…</div>
        ) : loadError ? (
          <div className="fed__empty fed__empty--err">{loadError}</div>
        ) : (
          <>
            {truncated ? (
              <div className="fed__warn">
                Este arquivo é grande e foi truncado na leitura. Salvar apagaria o
                restante — a edição está desabilitada.
              </div>
            ) : null}
            <textarea
              className="fed__area"
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                setSaved(null);
              }}
              spellCheck={false}
              readOnly={truncated}
              wrap="off"
            />
            <div className="fed__foot">
              <span className="fed__status">
                {saveError ? (
                  <span className="fed__err">{saveError}</span>
                ) : saved ? (
                  <span className="fed__ok">
                    {saved.created ? "Arquivo criado." : "Salvo."}
                    {saved.backup_path ? ` Backup guardado.` : ""}
                  </span>
                ) : dirty ? (
                  "Alterações não salvas"
                ) : (
                  "Sem alterações"
                )}
              </span>
              {confirming ? (
                <div className="fed__confirm">
                  <span>Sobrescrever o arquivo? Um backup será guardado.</span>
                  <button className="fed__save" onClick={doSave} disabled={saving}>
                    {saving ? "Salvando…" : "Salvar"}
                  </button>
                  <button className="fed__cancel" onClick={() => setConfirming(false)}>
                    Cancelar
                  </button>
                </div>
              ) : (
                <button
                  className="fed__save"
                  onClick={() => setConfirming(true)}
                  disabled={truncated || !dirty || saving}
                  title={truncated ? "Arquivo truncado — não é seguro salvar" : "Salvar"}
                >
                  Salvar
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
