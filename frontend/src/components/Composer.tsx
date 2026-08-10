import type { KeyboardEvent } from "react";

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
}: ComposerProps) {
  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter envia; Shift+Enter quebra linha.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const placeholder = disabled
    ? "Conectando ao backend…"
    : listening
      ? "Ouvindo… fale agora"
      : "Escreva sua mensagem…";

  return (
    <div className="composer">
      <div className="composer__row">
        <button
          type="button"
          className={`composer__mic ${listening ? "composer__mic--on" : ""}`}
          onClick={onToggleListen}
          disabled={disabled}
          title={listening ? "Parar de ouvir" : "Falar (microfone)"}
          aria-pressed={listening}
        >
          {listening ? "■" : "🎤"}
        </button>
        <textarea
          className="composer__input"
          placeholder={placeholder}
          value={value}
          disabled={disabled}
          rows={1}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
        />
        {speaking ? (
          <button
            type="button"
            className="composer__stop"
            onClick={onStopSpeaking}
            title="Interromper a fala da Friday"
          >
            ⏹ Parar
          </button>
        ) : (
          <button
            className="composer__send"
            onClick={submit}
            disabled={disabled || !value.trim()}
            title="Enviar (Enter)"
          >
            {busy ? "…" : "Enviar"}
          </button>
        )}
      </div>
      <label className="composer__autosend" title="Enviar a fala automaticamente ao terminar">
        <input
          type="checkbox"
          checked={autoSend}
          onChange={(e) => onToggleAutoSend(e.target.checked)}
        />
        Enviar a fala automaticamente
      </label>
    </div>
  );
}
