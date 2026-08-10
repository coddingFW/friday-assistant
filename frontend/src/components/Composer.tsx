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
  handsFree,
  onToggleHandsFree,
  wakeWord,
  onChangeWakeWord,
  requireWakeWord,
  onToggleRequireWake,
}: ComposerProps) {
  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const placeholder = disabled
    ? "Conectando ao backend…"
    : handsFree
      ? requireWakeWord
        ? `Mãos-livres — diga "${wakeWord}" para falar`
        : "Mãos-livres — pode falar"
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
          disabled={disabled || handsFree}
          title={
            handsFree
              ? "Microfone automático (mãos-livres)"
              : listening
                ? "Parar de ouvir"
                : "Falar (microfone)"
          }
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

      <div className="composer__opts">
        <label className="composer__toggle" title="Conversa contínua por voz, sem clicar">
          <input
            type="checkbox"
            checked={handsFree}
            onChange={(e) => onToggleHandsFree(e.target.checked)}
          />
          Mãos-livres
        </label>

        {handsFree ? (
          <label className="composer__toggle" title="Só responder quando você chamar pelo nome">
            <input
              type="checkbox"
              checked={requireWakeWord}
              onChange={(e) => onToggleRequireWake(e.target.checked)}
            />
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
            <input
              type="checkbox"
              checked={autoSend}
              onChange={(e) => onToggleAutoSend(e.target.checked)}
            />
            Enviar a fala automaticamente
          </label>
        )}
      </div>
    </div>
  );
}
