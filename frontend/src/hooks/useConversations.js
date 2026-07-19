import { useState, useCallback, useEffect } from "react";
import { resetConversation } from "../api/client";

const HISTORY_KEY = "tripweaver_conversations";
const ACTIVE_KEY = "tripweaver_active_conversation";

function loadConversations() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
  } catch {
    return [];
  }
}

function truncate(text, max) {
  if (text.length <= max) return text;
  return text.slice(0, max - 1) + "…";
}

// Honest scope note: there's no backend database of past conversations -
// the FastAPI backend only keeps one in-memory state per session_id for
// as long as the server process runs. This hook stores full transcripts
// in localStorage, keyed by the real session_id once the backend assigns
// one, so history survives page reloads without needing a new backend
// endpoint. "Delete" removes both the local copy AND asks the backend to
// forget its in-memory state for that session, via the existing /reset
// endpoint.
export function useConversations() {
  const [conversations, setConversations] = useState(loadConversations);
  const [activeId, setActiveId] = useState(() => localStorage.getItem(ACTIVE_KEY));
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => {
    if (activeId) localStorage.setItem(ACTIVE_KEY, activeId);
    else localStorage.removeItem(ACTIVE_KEY);
  }, [activeId]);

  const appendMessage = useCallback(
    (role, text, sessionId, extra = {}) => {
      const newMsg = { role, text, ...extra };
      setMessages((prev) => [...prev, newMsg]);

      setConversations((prev) => {
        let list = [...prev];
        let convo = list.find((c) => c.id === activeId);

        if (!convo) {
          convo = {
            id: sessionId || null,
            title: role === "user" ? truncate(text, 40) : "New chat",
            timestamp: Date.now(),
            messages: [],
          };
          list = [convo, ...list];
          if (sessionId) setActiveId(sessionId);
        } else if (sessionId && convo.id !== sessionId) {
          convo.id = sessionId;
          setActiveId(sessionId);
        }

        convo.messages = [...convo.messages, newMsg];
        convo.timestamp = Date.now();
        return list;
      });
    },
    [activeId]
  );

  const loadConversation = useCallback(
    (id) => {
      const convo = conversations.find((c) => c.id === id);
      if (!convo) return;
      setActiveId(id);
      setMessages(convo.messages);
    },
    [conversations]
  );

  const startNewConversation = useCallback(() => {
    setActiveId(null);
    setMessages([]);
  }, []);

  const deleteConversation = useCallback(
    async (id) => {
      if (id) {
        try {
          await resetConversation(id);
        } catch {
          // backend might already be gone/unreachable - still clear
          // the local copy so the UI stays consistent either way
        }
      }
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (id === activeId) {
        setActiveId(null);
        setMessages([]);
      }
    },
    [activeId]
  );

  const deleteActiveConversation = useCallback(() => {
    deleteConversation(activeId);
  }, [activeId, deleteConversation]);

  return {
    conversations: [...conversations].sort((a, b) => b.timestamp - a.timestamp),
    activeId,
    messages,
    appendMessage,
    loadConversation,
    startNewConversation,
    deleteConversation,
    deleteActiveConversation,
  };
}
