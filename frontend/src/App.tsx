import { useEffect, useRef, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { ContextPanel } from "./components/ContextPanel";
import { AvatarCustomizer } from "./components/AvatarCustomizer";
import { Composer } from "./components/Composer";
import { MessageList } from "./components/MessageList";
import { VoiceView } from "./components/VoiceView";
import { Icon } from "./components/Icon";
import { useChat } from "./hooks/useChat";
import { useWorkspace } from "./hooks/useWorkspace";
import { useConversations } from "./hooks/useConversations";
import { getConversation, getHealth } from "./services/api";
import type { ChatMessage, HealthResponse, StatusState } from "./types";

const STATUS_LABEL: Partial<Record<StatusState, string>> = {
  thinking: "Pensando…",
  searching: "Buscando na web…",
  responding: "Respondendo…",
  listening: "Ouvindo…",
};

const AVATAR_PREF_KEY = "friday.showAvatar";

function readAvatarPref(): boolean {
  try {
    return localStorage.getItem(AVATAR_PREF_KEY) === "1";
  } catch {
    return false;
  }
}

export default function App() {
  const workspace = useWorkspace();
  const chat = useChat({ contextFiles: workspace.selected });
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
    ocr,
    ocrBusy,
    handsFree,
    setHandsFree,
    wakeWord,
    setWakeWord,
    requireWakeWord,
    setRequireWakeWord,
  } = chat;
  const conversations = useConversations(conversationId);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [customizing, setCustomizing] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [contextOpen, setContextOpen] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [showAvatar, setShowAvatarState] = useState(readAvatarPref);

  const setShowAvatar = (v: boolean) => {
    setShowAvatarState(v);
    try {
      localStorage.setItem(AVATAR_PREF_KEY, v ? "1" : "0");
    } catch {
      /* preferência só nesta sessão */
    }
  };

  const resume = (id: string) => {
    setSidebarOpen(false);
    if (id === conversationId) return;
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
        setResumeError(e instanceof Error ? e.message : "Falha ao abrir a conversa.");
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

  // Ao fim de um turno, recarrega o histórico (título/ordem). O backend persiste
  // o turno logo APÓS emitir "idle": o atraso evita ler antes da gravação.
  const prevStatus = useRef(status);
  const refreshConversations = conversations.refresh;
  useEffect(() => {
    const prev = prevStatus.current;
    prevStatus.current = status;
    const wasTurn = prev === "thinking" || prev === "searching" || prev === "responding";
    if (wasTurn && status === "idle" && conversationId) {
      const t = setTimeout(() => refreshConversations(), 500);
      return () => clearTimeout(t);
    }
  }, [status, conversationId, refreshConversations]);

  const busy = status !== "idle" && status !== "listening";
  const codeMode = workspace.selected.length > 0;
  const shownError = error ?? resumeError;
  const title =
    conversations.items.find((c) => c.id === conversationId)?.title ?? "Nova conversa";
  const model = codeMode ? health?.code_model : health?.llm_model;

  if (handsFree) {
    return (
      <>
        <VoiceView
          status={status}
          messages={messages}
          requireWakeWord={requireWakeWord}
          wakeWord={wakeWord}
          muted={muted}
          onToggleMuted={setMuted}
          speaking={speaking}
          onStopSpeaking={stopSpeaking}
          onExit={() => setHandsFree(false)}
          showAvatar={showAvatar}
        />
        <AvatarCustomizer open={customizing} onClose={() => setCustomizing(false)} />
      </>
    );
  }

  return (
    <div className="shell">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        conversations={conversations.items}
        activeId={conversationId}
        conversationsError={conversations.error}
        onNew={() => {
          newConversation();
          setSidebarOpen(false);
        }}
        onSelect={resume}
        onDelete={(id) => {
          void conversations.remove(id);
          if (id === conversationId) newConversation();
        }}
        root={workspace.root}
        entries={workspace.entries}
        selected={workspace.selected}
        wsLoading={workspace.loading}
        wsError={workspace.error}
        onOpenRoot={workspace.openRoot}
        onToggleSelect={workspace.toggleSelect}
        onFileSaved={workspace.refresh}
        llmReachable={health ? health.llm_reachable : null}
        onCustomize={() => setCustomizing(true)}
      />

      <main className="main">
        <header className="topbar">
          <div className="topbar__left">
            <button type="button" className="icon-btn topbar__menu" onClick={() => setSidebarOpen(true)} aria-label="Abrir navegação">
              <Icon name="menu" />
            </button>
            <h1 className="topbar__title">{title}</h1>
          </div>
          <div className="topbar__right">
            {STATUS_LABEL[status] ? <span className="topbar__status">{STATUS_LABEL[status]}</span> : null}
            <span className="pill" title={codeMode ? "Arquivos do projeto no contexto: modelo de código" : "Conversa geral"}>
              <span className={`dot ${connected ? "dot--ok" : "dot--danger"}`} aria-label={connected ? "conectado" : "desconectado"} />
              {codeMode ? "Código" : "Conversa"}
              {model ? <span className="pill__model mono">{model}</span> : null}
            </span>
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => setHandsFree(true)} disabled={!connected} title="Conversa contínua por voz">
              <Icon name="waves" size={15} />
              Voz
            </button>
            <button
              type="button"
              className="icon-btn topbar__panel"
              onClick={() => setContextOpen((v) => !v)}
              aria-pressed={contextOpen}
              aria-label="Painel de contexto"
              title="Painel de contexto"
            >
              <Icon name="panelRight" />
            </button>
          </div>
        </header>

        <div className="main__scroll">
          <div className="column">
            <MessageList messages={messages} codeMode={codeMode} />
          </div>
        </div>

        <div className="main__composer">
          <div className="column">
            {shownError ? (
              <div className="alert" role="alert">
                {shownError}
              </div>
            ) : null}
            <Composer
              value={draft}
              onChange={setDraft}
              onSend={(text) => {
                send(text);
                setDraft("");
              }}
              disabled={!connected}
              busy={busy}
              codeMode={codeMode}
              listening={listening}
              onToggleListen={toggleListening}
              speaking={speaking}
              onStopSpeaking={stopSpeaking}
              muted={muted}
              onToggleMuted={setMuted}
              contextFiles={workspace.selected}
              onRemoveContextFile={workspace.toggleSelect}
              pendingImage={pendingImage}
              onAttachImage={attachImageFile}
              onCaptureScreen={captureScreen}
              onClearImage={clearImage}
              onOcr={ocr}
              ocrBusy={ocrBusy}
            />
          </div>
        </div>
      </main>

      {contextOpen ? <div className="scrim scrim--context" onClick={() => setContextOpen(false)} aria-hidden="true" /> : null}
      <ContextPanel
        open={contextOpen}
        selected={workspace.selected}
        entries={workspace.entries}
        numCtx={health?.code_num_ctx ?? null}
        onRemoveFile={workspace.toggleSelect}
        onClearFiles={workspace.clearSelected}
        status={status}
        handsFree={handsFree}
        onHandsFree={setHandsFree}
        muted={muted}
        onMuted={setMuted}
        autoSend={autoSend}
        onAutoSend={setAutoSend}
        requireWakeWord={requireWakeWord}
        onRequireWakeWord={setRequireWakeWord}
        wakeWord={wakeWord}
        onWakeWord={setWakeWord}
        showAvatar={showAvatar}
        onShowAvatar={setShowAvatar}
      />

      <AvatarCustomizer open={customizing} onClose={() => setCustomizing(false)} />
    </div>
  );
}
