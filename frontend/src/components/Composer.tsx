import { useLayoutEffect, useRef } from "react";
import type { ClipboardEvent, KeyboardEvent } from "react";

interface ComposerProps {
  value: string;
  onChange: (text: string) => void;
  onSend: (text: string) => void;
  disabled: boolean;
  busy: boolean;
  listening: boolean;
  onToggleListen: () => void;
  autoSend: boolean;
  onToggleAutoSend: (value: boolean) => void;
  speaking: boolean;
  onStopSpeaking: () => void;
  muted: boolean;
  onToggleMuted: (value: boolean) => void;
  contextCount: number;
  onClearContext: () => void;
  pendingImage: string | null;
  onAttachImage: (file: File) => void;
  onCaptureScreen: () => void;
  onClearImage: () => void;
  onOcr: () => void;
  ocrBusy: boolean;
  handsFree: boolean;
  onToggleHandsFree: (value: boolean) => void;
  wakeWord: string;
  onChangeWakeWord: (value: string) => void;
  requireWakeWord: boolean;
  onToggleRequireWake: (value: boolean) => void;
}

export function Composer({
  value,
  onChange,
  onSend,
  disabled,
  busy,
  listening,
  onToggleListen,
  autoSend,
  onToggleAutoSend,
  speaking,
  onStopSpeaking,
  muted,
  onToggleMuted,
  contextCount,
  onClearContext,
  pendingImage,
  onAttachImage,
  onCaptureScreen,
  onClearImage,
  onOcr,
  ocrBusy,
  handsFree,
  onToggleHandsFree,
  wakeWord,
  onChangeWakeWord,
  requireWakeWord,
  onToggleRequireWake,
}: ComposerProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-expande o campo conforme o conteúdo (até o max-height da CSS = 160px);
  // passando disso, rola internamente. Reavalia a cada mudança de `value` —
  // inclusive quando o texto é injetado por fora (ex.: OCR 🔤) ou pela voz.
  const MAX_INPUT_H = 160;
  useLayoutEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(el.scrollHeight, MAX_INPUT_H);
    el.style.height = `${next}px`;
    el.style.overflowY = el.scrollHeight > MAX_INPUT_H ? "auto" : "hidden";
  }, [value]);

  const submit = () => {
    if (disabled) return;
    if (!value.trim() && !pendingImage) return;
    onSend(value);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  // Colar (Ctrl+V) uma imagem do clipboard anexa direto, sem o botão.
  const onPaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
      if (item.kind === "file" && item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) {
          e.preventDefault();
          onAttachImage(file);
          return;
        }
      }
    }
  };

  const placeholder = disabled
    ? "Conectando ao backend…"
    : handsFree
      ? requireWakeWord
        ? `Mãos-livres — diga "${wakeWord}" para falar`
        : "Mãos-livres — pode falar"
      : pendingImage
        ? "O que você quer saber sobre a imagem?"
        : listening
          ? "Ouvindo… fale agora"
          : "Escreva sua mensagem…";

  return (
    <div className="composer">
      {contextCount > 0 ? (
        <div className="composer__ctx" title="Arquivos do projeto no contexto">
          <span className="composer__ctx-label">
            {contextCount} {contextCount === 1 ? "arquivo" : "arquivos"} no contexto
          </span>
          <button
            type="button"
            className="composer__ctx-x"
            onClick={onClearContext}
            title="Limpar contexto"
          >
            ✕
          </button>
        </div>
      ) : null}

      {pendingImage ? (
        <div className="composer__attach">
          <img src={pendingImage} alt="anexo" />
          <span className="composer__attach-label">imagem anexada</span>
          <button
            type="button"
            className="composer__attach-x"
            onClick={onClearImage}
            title="Remover imagem"
          >
            ✕
          </button>
        </div>
      ) : null}

      <textarea
        ref={inputRef}
        className="composer__input"
        placeholder={placeholder}
        value={value}
        disabled={disabled}
        rows={1}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        onPaste={onPaste}
      />

      <div className="composer__row">
        <button
          type="button"
          className={`composer__mic ${listening ? "composer__mic--on" : ""}`}
          onClick={onToggleListen}
          disabled={disabled || handsFree}
          title={handsFree ? "Microfone automático (mãos-livres)" : listening ? "Parar de ouvir" : "Falar (microfone)"}
          aria-pressed={listening}
        >
          {listening ? "■" : "🎤"}
        </button>
        <button
          type="button"
          className="composer__icon"
          onClick={() => fileRef.current?.click()}
          disabled={disabled}
          title="Anexar imagem"
        >
          📎
        </button>
        <button
          type="button"
          className="composer__icon"
          onClick={onCaptureScreen}
          disabled={disabled}
          title="Capturar a tela"
        >
          🖥️
        </button>
        <button
          type="button"
          className="composer__icon"
          onClick={onOcr}
          disabled={disabled || ocrBusy}
          title={
            pendingImage
              ? "Ler o texto da imagem (OCR)"
              : "Ler o texto da tela (OCR)"
          }
        >
          {ocrBusy ? "…" : "🔤"}
        </button>
        <button
          type="button"
          className={`composer__icon ${muted ? "composer__icon--muted" : ""}`}
          onClick={() => onToggleMuted(!muted)}
          title={muted ? "Voz silenciada — clique para ouvir a Friday" : "Silenciar a voz da Friday"}
          aria-pressed={muted}
        >
          {muted ? "🔇" : "🔊"}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onAttachImage(file);
            e.target.value = "";
          }}
        />
        {speaking ? (
          <button type="button" className="composer__stop composer__send--right" onClick={onStopSpeaking} title="Interromper a fala da Friday">
            ⏹ Parar
          </button>
        ) : (
          <button
            className="composer__send composer__send--right"
            onClick={submit}
            disabled={disabled || (!value.trim() && !pendingImage)}
            title="Enviar (Enter)"
          >
            {busy ? "…" : "Enviar"}
          </button>
        )}
      </div>

      <div className="composer__opts">
        <label className="composer__toggle" title="Conversa contínua por voz, sem clicar">
          <input type="checkbox" checked={handsFree} onChange={(e) => onToggleHandsFree(e.target.checked)} />
          Mãos-livres
        </label>

        {handsFree ? (
          <label className="composer__toggle" title="Só responder quando você chamar pelo nome">
            <input type="checkbox" checked={requireWakeWord} onChange={(e) => onToggleRequireWake(e.target.checked)} />
            chamar por
            <input
              className="composer__wake"
              type="text"
              value={wakeWord}
              disabled={!requireWakeWord}
              onChange={(e) => onChangeWakeWord(e.target.value)}
              aria-label="Palavra de ativação"
            />
          </label>
        ) : (
          <label className="composer__toggle" title="Enviar a fala automaticamente ao terminar">
            <input type="checkbox" checked={autoSend} onChange={(e) => onToggleAutoSend(e.target.checked)} />
            Enviar a fala automaticamente
          </label>
        )}
      </div>
    </div>
  );
}
