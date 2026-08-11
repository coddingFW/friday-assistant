import { useRef } from "react";
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
  pendingImage: string | null;
  onAttachImage: (file: File) => void;
  onCaptureScreen: () => void;
  onClearImage: () => void;
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
  pendingImage,
  onAttachImage,
  onCaptureScreen,
  onClearImage,
  handsFree,
  onToggleHandsFree,
  wakeWord,
  onChangeWakeWord,
  requireWakeWord,
  onToggleRequireWake,
}: ComposerProps) {
  const fileRef = useRef<HTMLInputElement>(null);

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
          <button type="button" className="composer__stop" onClick={onStopSpeaking} title="Interromper a fala da Friday">
            ⏹ Parar
          </button>
        ) : (
          <button
            className="composer__send"
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
