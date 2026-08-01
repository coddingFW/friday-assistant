import { useState } from "react";
import type { KeyboardEvent } from "react";

interface ComposerProps {
  onSend: (text: string) => void;
  disabled: boolean;
  busy: boolean;
}

export function Composer({ onSend, disabled, busy }: ComposerProps) {
  const [text, setText] = useState("");

  const submit = () => {
    const value = text.trim();
    if (!value || disabled) return;
    onSend(value);
    setText("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter envia; Shift+Enter quebra linha.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="composer">
      <textarea
        className="composer__input"
        placeholder={disabled ? "Conectando ao backend…" : "Escreva sua mensagem…"}
        value={text}
        disabled={disabled}
        rows={1}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
      />
      <button
        className="composer__send"
        onClick={submit}
        disabled={disabled || !text.trim()}
        title="Enviar (Enter)"
      >
        {busy ? "…" : "Enviar"}
      </button>
    </div>
  );
}
