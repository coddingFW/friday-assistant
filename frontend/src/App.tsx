import { useEffect, useRef, useState } from "react";
import { Header } from "./components/Header";
import { FriendlyAvatar } from "./components/FriendlyAvatar";
import { AvatarCustomizer } from "./components/AvatarCustomizer";
import { Composer } from "./components/Composer";
import { MessageList } from "./components/MessageList";
import { WorkspacePanel } from "./components/WorkspacePanel";
import { HistoryPanel } from "./components/HistoryPanel";
import { useChat } from "./hooks/useChat";
import { useWorkspace } from "./hooks/useWorkspace";
import { useConversations } from "./hooks/useConversations";
import { getConversation, getHealth } from "./services/api";
import type { ChatMessage, HealthResponse } from "./types";

export default function App() {
  const workspace = useWorkspace();
  const {
    messages,
    status,
    connected,
    error,
    conversationId,
    newConversation,
    resumeConversation,
    send,
    draft,
    setDraft,
    listening,
    toggleListening,
    autoSend,
    setAutoSend,
    speaking,
    stopSpeaking,
    muted,
    setMuted,
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
  } = useChat({ contextFiles: workspace.selected });
  const conversations = useConversations(conversationId);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [customizing, setCustomizing] = useState(false);
  const [showProject, setShowProject] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);

  const resume = (id: string) => {
    if (id === conversationId) return; // já é a conversa aberta
    setResumeError(null);
    void (async () => {
      try {
        const detail = await getConversation(id);
        const history: ChatMessage[] = detail.messages.map((m, i) => ({
          id: `${id}-${i}`,
          role: m.role,
          content: m.content,
        }));
        resumeConversation(id, history);
      } catch (e) {
        setResumeError(
          e instanceof Error ? e.message : "Falha ao abrir a conversa.",
        );
      }
    })();
  };

  useEffect(() => {
    let alive = true;
    getHealth()
      .then((h) => alive && setHealth(h))
      .catch(() => alive && setHealth(null));
    return () => {
      alive = false;
    };
  }, []);

  // Ao fim de um turno, recarrega o histórico para refletir a contagem/ordem da
  // conversa. O backend persiste o turno logo APÓS emitir "idle", então há um
  // pequeno atraso para não ler o banco antes da gravação (corrida conhecida).
  const prevStatus = useRef(status);
  const refreshConversations = conversations.refresh;
  useEffect(() => {
    const prev = prevStatus.current;
    prevStatus.current = status;
    const wasTurn =
      prev === "thinking" || prev === "searching" || prev === "responding";
    if (wasTurn && status === "idle" && conversationId) {
      const t = setTimeout(() => refreshConversations(), 500);
      return () => clearTimeout(t);
    }
  }, [status, conversationId, refreshConversations]);

  const busy = status !== "idle";
  const contextCount = workspace.selected.length;
  const shownError = error ?? resumeError;

  return (
    <div className={`app ${showProject || showHistory ? "app--panel" : ""}`}>
      <Header
        health={health}
        connected={connected}
        status={status}
        codeActive={contextCount > 0}
        projectOpen={showProject}
        onToggleProject={() => setShowProject((v) => !v)}
        historyOpen={showHistory}
        onToggleHistory={() => setShowHistory((v) => !v)}
        onCustomize={() => setCustomizing(true)}
      />
      <div className="app__body">
        {showHistory ? (
          <HistoryPanel
            items={conversations.items}
            activeId={conversationId}
            loading={conversations.loading}
            error={conversations.error}
            onNew={newConversation}
            onSelect={resume}
            onDelete={(id) => {
              void conversations.remove(id);
              if (id === conversationId) newConversation();
            }}
            onRefresh={conversations.refresh}
            onClose={() => setShowHistory(false)}
          />
        ) : null}
        {showProject ? (
          <WorkspacePanel
            root={workspace.root}
            entries={workspace.entries}
            selected={workspace.selected}
            loading={workspace.loading}
            error={workspace.error}
            onOpen={workspace.openRoot}
            onToggleSelect={workspace.toggleSelect}
            onClearSelected={workspace.clearSelected}
            onClose={() => setShowProject(false)}
            onFileSaved={workspace.refresh}
          />
        ) : null}
        <div className="app__content">
          <div className="app__stage">
            <FriendlyAvatar status={status} />
          </div>
          <main className="app__main">
            <MessageList messages={messages} />
          </main>
          {shownError ? <div className="banner banner--error">{shownError}</div> : null}
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
              muted={muted}
              onToggleMuted={setMuted}
              contextCount={contextCount}
              onClearContext={workspace.clearSelected}
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
        </div>
      </div>
      <AvatarCustomizer open={customizing} onClose={() => setCustomizing(false)} />
    </div>
  );
}
