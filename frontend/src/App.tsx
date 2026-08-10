import { useEffect, useState } from "react";
import { Header } from "./components/Header";
import { Avatar3D } from "./components/Avatar3D";
import { Composer } from "./components/Composer";
import { MessageList } from "./components/MessageList";
import { useChat } from "./hooks/useChat";
import { getHealth } from "./services/api";
import type { HealthResponse } from "./types";

export default function App() {
  const {
    messages,
    status,
    connected,
    error,
    send,
    draft,
    setDraft,
    listening,
    toggleListening,
    autoSend,
    setAutoSend,
    speaking,
    stopSpeaking,
  } = useChat();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let alive = true;
    getHealth()
      .then((h) => alive && setHealth(h))
      .catch(() => alive && setHealth(null));
    return () => {
      alive = false;
    };
  }, []);

  const busy = status !== "idle";

  return (
    <div className="app">
      <Header health={health} connected={connected} status={status} />
      <div className="app__stage">
        <Avatar3D status={status} />
      </div>
      <main className="app__main">
        <MessageList messages={messages} />
      </main>
      {error ? <div className="banner banner--error">{error}</div> : null}
      <footer className="app__footer">
        <Composer
          value={draft}
          onChange={setDraft}
          onSend={(text) => {
            send(text);
            setDraft("");
          }}
          disabled={!connected}
          busy={busy}
          listening={listening}
          onToggleListen={toggleListening}
          autoSend={autoSend}
          onToggleAutoSend={setAutoSend}
          speaking={speaking}
          onStopSpeaking={stopSpeaking}
        />
      </footer>
    </div>
  );
}
