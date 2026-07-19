import { useEffect, useRef, useState } from "react";
import Navbar from "./components/Navbar";
import HistorySidebar from "./components/HistorySidebar";
import ChatMessage from "./components/ChatMessage";
import Hero from "./components/Hero";
import { HotelCards, FlightCards } from "./components/ResultCards";
import { StatusLine, QuickReplies } from "./components/StatusLine";
import ChatInput from "./components/ChatInput";
import { useConversations } from "./hooks/useConversations";
import { streamChat } from "./api/client";

export default function App() {
  const {
    conversations,
    activeId,
    messages,
    appendMessage,
    loadConversation,
    startNewConversation,
    deleteConversation,
    deleteActiveConversation,
  } = useConversations();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [statusLabel, setStatusLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastUserMessage, setLastUserMessage] = useState(null);
  const chatLogRef = useRef(null);

  useEffect(() => {
    if (chatLogRef.current) {
      chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
    }
  }, [messages, statusLabel]);

  async function handleSend(text) {
    setLastUserMessage(text);
    appendMessage("user", text, activeId);
    setBusy(true);
    setStatusLabel("");

    let assistantText = "";
    let firstTokenReceived = false;
    let finalSessionId = null;
    let finalHotels = null;
    let finalFlights = null;
    let erroredOut = false;

    await streamChat(text, activeId, (event) => {
      switch (event.type) {
        case "status":
          setStatusLabel(event.label || "Working...");
          break;
        case "token":
          if (!firstTokenReceived) {
            firstTokenReceived = true;
            setStatusLabel("");
          }
          assistantText += event.text;
          break;
        case "done":
          finalSessionId = event.session_id;
          finalHotels = event.hotels;
          finalFlights = event.flights;
          setStatusLabel("");
          break;
        case "error":
          erroredOut = true;
          assistantText = event.message || "Something went wrong. Please try again.";
          setStatusLabel("");
          break;
      }
    });

    appendMessage("assistant", assistantText || "Something went wrong.", finalSessionId, {
      isError: erroredOut,
      hotels: finalHotels,
      flights: finalFlights,
    });

    setBusy(false);
  }

  function handleRetry() {
    if (lastUserMessage) handleSend(lastUserMessage);
  }

  function handleDeleteChat() {
    if (!activeId && messages.length === 0) return;
    if (window.confirm("Delete this conversation? This can't be undone.")) {
      deleteActiveConversation();
    }
  }

  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");

  return (
    <div className="h-screen flex flex-col relative overflow-hidden bg-canvas">
      {/* Background photo - heavily blurred and dark-overlaid so it reads
          as an atmospheric backdrop, and so every message stays clearly
          legible on top of it regardless of scroll position. */}
      <div
        className="absolute inset-0 bg-cover bg-center opacity-25 blur-2xl scale-110"
        style={{ backgroundImage: "url(/images/beach-bg.jpg)" }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-canvas/80 via-canvas/90 to-canvas" />

      <div className="relative z-10 flex flex-col h-full">
        <Navbar
          onToggleHistory={() => setSidebarOpen((v) => !v)}
          onDeleteChat={handleDeleteChat}
          canDelete={messages.length > 0}
        />

        <HistorySidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          conversations={conversations}
          activeId={activeId}
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

        <main className="flex-1 flex flex-col max-w-3xl w-full mx-auto p-4 md:p-6 min-h-0">
          {messages.length === 0 ? (
            <Hero onSuggestionClick={handleSend} />
          ) : (
            <div
              ref={chatLogRef}
              className="chat-scroll flex-1 overflow-y-auto flex flex-col gap-3 px-1 py-2"
            >
              {messages.map((m, i) => (
                <div key={i} className="flex flex-col gap-2">
                  <ChatMessage
                    role={m.role}
                    text={m.text}
                    isError={m.isError}
                    onRetry={m.isError && m === lastAssistantMsg ? handleRetry : undefined}
                  />
                  {m.role === "assistant" && <HotelCards hotels={m.hotels} />}
                  {m.role === "assistant" && <FlightCards flights={m.flights} />}
                </div>
              ))}
              {lastAssistantMsg && lastAssistantMsg === messages[messages.length - 1] && (
                <QuickReplies
                  hotels={lastAssistantMsg.hotels}
                  flights={lastAssistantMsg.flights}
                  onReply={handleSend}
                />
              )}
            </div>
          )}

          <StatusLine label={statusLabel} />
          <div className="mt-1">
            <ChatInput onSend={handleSend} disabled={busy} />
          </div>
          <p className="text-center text-[11px] text-muted/60 mt-3">
            TripWeaver AI may produce inaccurate information. Verify important details before booking.
          </p>
        </main>
      </div>
    </div>
  );
}
