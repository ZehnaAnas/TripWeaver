import { useCallback, useEffect, useRef, useState } from "react";
import Navbar from "./components/Navbar";
import HistorySidebar from "./components/HistorySidebar";
import ChatMessage from "./components/ChatMessage";
import Hero from "./components/Hero";
import ActivityBoard from "./components/ActivityBoard";
import QuickReplies from "./components/QuickReplies";
import ChatInput from "./components/ChatInput";
import { useConversations } from "./hooks/useConversations";
import { useTheme } from "./hooks/useTheme";
import { streamChat } from "./api/client";

export default function App() {
  const {
    conversations,
    activeKey,
    sessionId,
    messages,
    appendMessage,
    loadConversation,
    startNewConversation,
    deleteConversation,
    deleteActiveConversation,
  } = useConversations();

  const { theme, toggleTheme } = useTheme();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [steps, setSteps] = useState([]);          // agent activity for this turn
  const [streamingText, setStreamingText] = useState(""); // live tokens
  const [busy, setBusy] = useState(false);
  const [lastUserMessage, setLastUserMessage] = useState(null);

  const chatLogRef = useRef(null);
  const abortRef = useRef(null);
  const stepIdRef = useRef(0);

  // Follow the tail of the conversation as tokens arrive, but only when the
  // reader is already near the bottom - scrolling back to re-read an earlier
  // plan shouldn't get yanked away mid-sentence.
  useEffect(() => {
    const el = chatLogRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 160;
    if (nearBottom) el.scrollTop = el.scrollHeight;
  }, [messages, streamingText, steps]);

  const handleSend = useCallback(
    async (text) => {
      if (busy) return;

      setLastUserMessage(text);
      appendMessage("user", text, sessionId);
      setBusy(true);
      setSteps([]);
      setStreamingText("");

      const controller = new AbortController();
      abortRef.current = controller;

      let assistantText = "";
      let firstTokenSeen = false;
      let finalSessionId = null;
      let resultKind = null;
      let erroredOut = false;

      await streamChat(
        text,
        sessionId,
        (event) => {
          switch (event.type) {
            // Each graph node reports in as it starts, which is what drives
            // the activity board (ROUTING -> SEARCHING -> RESPONDING).
            case "status":
              setSteps((prev) => {
                const last = prev[prev.length - 1];
                if (last && last.node === event.node) return prev;
                return [
                  ...prev,
                  {
                    id: ++stepIdRef.current,
                    node: event.node,
                    status: event.activity_status || "WORKING",
                    label: event.label || "Working",
                  },
                ];
              });
              break;

            // Tokens are appended to React state as they land, so the reply
            // renders word by word instead of appearing all at once.
            case "start":
              finalSessionId = event.session_id;
              break;
            case "token":
              if (!firstTokenSeen) {
                firstTokenSeen = true;
                setSteps([]);
              }
              assistantText += event.text;
              setStreamingText(assistantText);
              break;

            case "done":
              finalSessionId = event.session_id;
              if (event.hotels?.length) resultKind = "hotel";
              else if (event.flights?.length) resultKind = "flight";
              break;

            case "error":
              erroredOut = true;
              assistantText = event.message || "Something went wrong. Try again.";
              break;
          }
        },
        controller.signal
      );

      const aborted = controller.signal.aborted;
      abortRef.current = null;

      setStreamingText("");
      setSteps([]);
      setBusy(false);

      if (aborted) {
        // Keep whatever had already streamed in rather than throwing it away.
        if (assistantText.trim()) {
          appendMessage("assistant", assistantText + "\n\n_(stopped)_", finalSessionId, {
            resultKind,
          });
        }
        return;
      }

      appendMessage(
        "assistant",
        assistantText || "I didn't get an answer back that time. Try again.",
        finalSessionId,
        { isError: erroredOut, resultKind }
      );
    },
    [sessionId, appendMessage, busy]
  );

  function handleStop() {
    abortRef.current?.abort();
  }

  function handleRetry() {
    if (lastUserMessage) handleSend(lastUserMessage);
  }

  function handleDeleteChat() {
    if (!activeKey && messages.length === 0) return;
    if (window.confirm("Delete this conversation? This can't be undone.")) {
      deleteActiveConversation();
    }
  }

  const lastMessage = messages[messages.length - 1];
  const showQuickReplies =
    !busy && lastMessage?.role === "assistant" && !lastMessage.isError;

  return (
    <div className="relative flex h-[100dvh] flex-col overflow-hidden bg-canvas">
      {/* Atmospheric backdrop: blurred hard enough that it reads as light and
          colour rather than a photo, so text stays legible over it in both themes. */}
      <div
        className="pointer-events-none absolute inset-0 scale-110 bg-cover bg-center opacity-[0.10] blur-3xl dark:opacity-[0.18]"
        style={{ backgroundImage: "url(/images/beach-bg.jpg)" }}
      />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-canvas/60 via-canvas/85 to-canvas" />

      <div className="relative z-10 flex h-full flex-col">
        <Navbar
          onToggleHistory={() => setSidebarOpen((v) => !v)}
          onNewChat={startNewConversation}
          onDeleteChat={handleDeleteChat}
          canDelete={messages.length > 0}
          theme={theme}
          onToggleTheme={toggleTheme}
        />

        <HistorySidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          conversations={conversations}
          activeId={activeKey}
          onSelectConversation={(id) => {
            loadConversation(id);
            setSidebarOpen(false);
          }}
          onNewChat={() => {
            startNewConversation();
            setSidebarOpen(false);
          }}
          onDeleteConversation={deleteConversation}
        />

        <main className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col px-3 pb-3 md:px-6 md:pb-5">
          {messages.length === 0 && !busy ? (
            <Hero onSuggestionClick={handleSend} disabled={busy} />
          ) : (
            <div
              ref={chatLogRef}
              className="chat-scroll flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-1 py-4"
            >
              {messages.map((m, i) => (
                <ChatMessage
                  key={i}
                  role={m.role}
                  text={m.text}
                  isError={m.isError}
                  onRetry={m.isError && i === messages.length - 1 ? handleRetry : undefined}
                />
              ))}

              {streamingText && <ChatMessage role="assistant" text={streamingText} streaming />}

              {showQuickReplies && (
                <QuickReplies
                  resultKind={lastMessage.resultKind}
                  onReply={handleSend}
                  disabled={busy}
                />
              )}
            </div>
          )}

          <div className="pt-1">
            <ActivityBoard steps={steps} busy={busy} streaming={!!streamingText} />
            <ChatInput onSend={handleSend} onStop={handleStop} busy={busy} />
            <p className="mt-2.5 text-center text-[11px] text-muted/70">
              TripWeaver can get details wrong. Check prices and dates before you book.
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
