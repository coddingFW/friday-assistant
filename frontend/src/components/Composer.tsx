import { useLayoutEffect, useRef } from "react";
import type { ClipboardEvent, KeyboardEvent } from "react";
import { Icon } from "./Icon";

interface ComposerProps {
  value: string;
  onChange: (text: string) => void;
  onSend: (text: string) => void;
  disabled: boolean;
  busy: boolean;
  codeMode: boolean;
  listening: boolean;
  onToggleListen: () => void;
  speaking: boolean;
  onStopSpeaking: () => void;
  muted: boolean;
  onToggleMuted: (value: boolean) => void;
  contextFiles: string[];
  onRemoveContextFile: (path: string) => void;
  pendingImage: string | null;
  onAttachImage: (file: File) => void;
  onCaptureScreen: () => void;
  onClearImage: () => void;
  onOcr: () => void;
  ocrBusy: boolean;
}

/** Altura máxima do campo antes de rolar internamente. */
const MAX_INPUT_H = 200;

export function Composer({
  value,
  onChange,
  onSend,
  disabled,
  busy,
  codeMode,
  listening,
  onToggleListen,
  speaking,
  onStopSpeaking,
  muted,
  onToggleMuted,
  contextFiles,
  onRemoveContextFile,
  pendingImage,
  onAttachImage,
  onCaptureScreen,
  onClearImage,
  onOcr,
  ocrBusy,
}: ComposerProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-expande o campo conforme o conteúdo — inclusive quando o texto chega
  // por fora (OCR, ditado).
  useLayoutEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_INPUT_H)}px`;
    el.style.overflowY = el.scrollHeight > MAX_INPUT_H ? "auto" : "hidden";
  }, [value]);

  const canSend = !disabled && (value.trim().length > 0 || pendingImage !== null);

  const submit = () => {
    if (!canSend) return;
    onSend(value);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  // Colar (Ctrl+V) uma imagem do clipboard anexa direto.
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
    : listening
      ? "Ouvindo… fale agora"
      : pendingImage
        ? "O que você quer saber sobre a imagem?"
        : codeMode
          ? "Pergunte sobre o projeto…"
          : "Pergunte qualquer coisa…";

  const hasChips = contextFiles.length > 0 || pendingImage !== null;

  return (
    <div className={`composer ${listening ? "is-listening" : ""}`}>
      {hasChips ? (
        <div className="composer__chips">
          {pendingImage ? (
            <span className="chip chip--image">
              <img src={pendingImage} alt="" />
              Imagem
              <button type="button" className="chip__x" onClick={onClearImage} aria-label="Remover imagem">
                <Icon name="x" size={11} strokeWidth={2.5} />
              </button>
            </span>
          ) : null}
          {contextFiles.map((path) => (
            <span key={path} className="chip mono" title={path}>
              {path.split("/").pop()}
              <button
                type="button"
                className="chip__x"
                onClick={() => onRemoveContextFile(path)}
                aria-label={`Tirar ${path} do contexto`}
              >
                <Icon name="x" size={11} strokeWidth={2.5} />
              </button>
            </span>
          ))}
        </div>
      ) : null}

      <label className="composer__field">
        <span className="sr-only">Mensagem</span>
        <textarea
          ref={inputRef}
          placeholder={placeholder}
          value={value}
          disabled={disabled}
          rows={1}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
        />
      </label>

      <div className="composer__bar">
        <div className="composer__tools">
          <button type="button" className="icon-btn" onClick={() => fileRef.current?.click()} disabled={disabled} aria-label="Anexar imagem" title="Anexar imagem">
            <Icon name="paperclip" size={17} />
          </button>
          <button type="button" className="icon-btn" onClick={onCaptureScreen} disabled={disabled} aria-label="Capturar a tela" title="Capturar a tela">
            <Icon name="monitor" size={17} />
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={onOcr}
            disabled={disabled || ocrBusy}
            aria-label={pendingImage ? "Ler o texto da imagem (OCR)" : "Ler o texto da tela (OCR)"}
            title={pendingImage ? "Ler o texto da imagem (OCR)" : "Ler o texto da tela (OCR)"}
          >
            {ocrBusy ? <span className="spinner" aria-hidden="true" /> : <Icon name="scanText" size={17} />}
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={() => onToggleMuted(!muted)}
            aria-pressed={!muted}
            aria-label={muted ? "Voz da Friday desligada" : "Voz da Friday ligada"}
            title={muted ? "Ligar a voz da Friday" : "Silenciar a voz da Friday"}
          >
            <Icon name={muted ? "volumeOff" : "volume"} size={17} />
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
        </div>

        <div className="composer__actions">
          <span className="composer__hint">{busy ? "Gerando resposta…" : "Enter envia · Shift+Enter quebra linha"}</span>
          <button
            type="button"
            className={`icon-btn icon-btn--outline ${listening ? "is-recording" : ""}`}
            onClick={onToggleListen}
            disabled={disabled}
            aria-pressed={listening}
            aria-label={listening ? "Parar de ouvir" : "Falar"}
            title={listening ? "Parar de ouvir" : "Falar"}
          >
            <Icon name={listening ? "stop" : "mic"} size={17} />
          </button>
          {speaking ? (
            <button type="button" className="icon-btn icon-btn--primary" onClick={onStopSpeaking} aria-label="Interromper a fala" title="Interromper a fala">
              <Icon name="stop" size={15} />
            </button>
          ) : (
            <button type="button" className="icon-btn icon-btn--primary" onClick={submit} disabled={!canSend} aria-label="Enviar" title="Enviar (Enter)">
              <Icon name="arrowUp" size={17} strokeWidth={2.2} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
