import { useEffect, useState } from "react";
import { Header } from "./components/Header";
import { FriendlyAvatar } from "./components/FriendlyAvatar";
import { AvatarCustomizer } from "./components/AvatarCustomizer";
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
    pendingImage,
    attachImageFile,
    captureScreen,
    clearImage,
    handsFree,
    setHandsFree,
    wakeWord,
    setWakeWord,
    requireWakeWord,
    setRequireWakeWord,
  } = useChat();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [customizing, setCustomizing] = useState(false);

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
      <Header health={health} connected={connected} status={status} onCustomize={() => setCustomizing(true)} />
      <div className="app__stage">
        <FriendlyAvatar status={status} />
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
          pendingImage={pendingImage}
          onAttachImage={attachImageFile}
          onCaptureScreen={captureScreen}
          onClearImage={clearImage}
          handsFree={handsFree}
          onToggleHandsFree={setHandsFree}
          wakeWord={wakeWord}
          onChangeWakeWord={setWakeWord}
          requireWakeWord={requireWakeWord}
          onToggleRequireWake={setRequireWakeWord}
        />
      </footer>
      <AvatarCustomizer open={customizing} onClose={() => setCustomizing(false)} />
    </div>
  );
}
