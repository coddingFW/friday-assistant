// Painel direito: o que entra no próximo turno (arquivos + estimativa de tokens
// contra a janela do modelo de código), preferências de voz e o estado da Friday.

import type { StatusState, WsTreeEntry } from "../types";
import { Icon } from "./Icon";

/** ~3,5 caracteres por token para código: estimativa grosseira, só para orientar. */
const CHARS_PER_TOKEN = 3.5;

function formatK(n: number): string {
  if (n < 1000) return String(Math.round(n));
  return `${(n / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}k`;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} KB`;
}

const STATUS_LABEL: Record<StatusState, string> = {
  idle: "Pronta",
  thinking: "Pensando",
  searching: "Buscando na web",
  responding: "Respondendo",
  listening: "Ouvindo",
};

interface SwitchProps {
  id: string;
  label: string;
  hint?: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (value: boolean) => void;
}

function Switch({ id, label, hint, checked, disabled, onChange }: SwitchProps) {
  return (
    <div className="setting">
      <div className="setting__text">
        <span id={id}>{label}</span>
        {hint ? <span className="setting__hint">{hint}</span> : null}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={id}
        className="switch"
        disabled={disabled}
        onClick={() => onChange(!checked)}
      >
        <span className="switch__thumb" />
      </button>
    </div>
  );
}

interface ContextPanelProps {
  open: boolean;
  selected: string[];
  entries: WsTreeEntry[];
  numCtx: number | null;
  onRemoveFile: (path: string) => void;
  onClearFiles: () => void;
  status: StatusState;
  // Voz
  handsFree: boolean;
  onHandsFree: (v: boolean) => void;
  muted: boolean;
  onMuted: (v: boolean) => void;
  autoSend: boolean;
  onAutoSend: (v: boolean) => void;
  requireWakeWord: boolean;
  onRequireWakeWord: (v: boolean) => void;
  wakeWord: string;
  onWakeWord: (v: string) => void;
  showAvatar: boolean;
  onShowAvatar: (v: boolean) => void;
}

export function ContextPanel(p: ContextPanelProps) {
  const sizes = new Map(p.entries.map((e) => [e.path, e.size]));
  const totalBytes = p.selected.reduce((sum, path) => sum + (sizes.get(path) ?? 0), 0);
  const tokens = totalBytes / CHARS_PER_TOKEN;
  const pct = p.numCtx ? Math.min(100, Math.round((tokens / p.numCtx) * 100)) : 0;
  const over = p.numCtx !== null && tokens > p.numCtx * 0.9;

  return (
    <aside className={`context ${p.open ? "is-open" : ""}`} aria-label="Contexto e preferências">
      <section className="ctx-section">
        <div className="ctx-section__head">
          <h2 className="eyebrow">Contexto</h2>
          {p.selected.length ? (
            <button type="button" className="link-btn" onClick={p.onClearFiles}>
              Limpar
            </button>
          ) : null}
        </div>

        {p.selected.length === 0 ? (
          <p className="ctx-empty">
            Nenhum arquivo. Marque arquivos do projeto na barra lateral para a Friday responder sobre o seu código.
          </p>
        ) : (
          <>
            <div className="meter" aria-live="polite">
              <div className="meter__row">
                <span>
                  ≈ {formatK(tokens)}
                  {p.numCtx ? ` de ${formatK(p.numCtx)} tokens` : " tokens"}
                </span>
                {p.numCtx ? <span className="meter__pct">{pct}%</span> : null}
              </div>
              {p.numCtx ? (
                <div className="meter__bar">
                  <div className={`meter__fill ${over ? "is-over" : ""}`} style={{ width: `${pct}%` }} />
                </div>
              ) : null}
              {over ? (
                <p className="meter__warn">Perto do limite: parte dos arquivos pode ficar de fora.</p>
              ) : null}
            </div>
            <ul className="ctx-files">
              {p.selected.map((path) => (
                <li key={path} className="ctx-file">
                  <span className="ctx-file__name mono" title={path}>
                    {path.split("/").pop()}
                  </span>
                  <span className="ctx-file__size">{formatSize(sizes.get(path) ?? 0)}</span>
                  <button
                    type="button"
                    className="icon-btn icon-btn--xs"
                    onClick={() => p.onRemoveFile(path)}
                    aria-label={`Tirar ${path} do contexto`}
                  >
                    <Icon name="x" size={12} />
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="ctx-section">
        <h2 className="eyebrow">Voz</h2>
        <Switch id="sw-handsfree" label="Mãos-livres" hint="Conversa contínua, sem clicar" checked={p.handsFree} onChange={p.onHandsFree} />
        <Switch id="sw-read" label="Ler respostas em voz alta" checked={!p.muted} onChange={(v) => p.onMuted(!v)} />
        <Switch id="sw-autosend" label="Enviar a fala sozinha" hint="Ao terminar de falar" checked={p.autoSend} onChange={p.onAutoSend} />
        <Switch
          id="sw-wake"
          label="Só responder quando chamada"
          checked={p.requireWakeWord}
          onChange={p.onRequireWakeWord}
        />
        {p.requireWakeWord ? (
          <label className="field">
            <span className="field__label">Palavra de ativação</span>
            <input className="input" value={p.wakeWord} onChange={(e) => p.onWakeWord(e.target.value)} />
          </label>
        ) : null}
        <Switch id="sw-avatar" label="Mostrar avatar no modo voz" checked={p.showAvatar} onChange={p.onShowAvatar} />
      </section>

      <section className="presence" aria-live="polite">
        <span className={`presence__orb ${p.status !== "idle" ? "is-active" : ""}`} aria-hidden="true">
          <span />
        </span>
        <div className="presence__text">
          <span className="presence__state">{STATUS_LABEL[p.status]}</span>
          <span className="presence__hint">
            {p.requireWakeWord ? `Diga “${p.wakeWord}” no modo mãos-livres` : "Pronta para ouvir ou ler"}
          </span>
        </div>
      </section>
    </aside>
  );
}
