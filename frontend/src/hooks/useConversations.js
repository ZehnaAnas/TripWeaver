import { useCallback, useEffect, useRef, useState } from "react";
import { resetConversation } from "../api/client";

const HISTORY_KEY = "tripweaver_conversations";
const ACTIVE_KEY = "tripweaver_active_conversation";

/**
 * Honest scope note: there is no backend database of past conversations.
 * The FastAPI backend keeps one in-memory LangGraph checkpoint per
 * session_id, for as long as the server process lives. This hook stores the
 * full transcripts in localStorage so history survives a page reload without
 * needing a new backend endpoint.
 *
 * Two different identifiers are deliberately kept apart:
 *   - `key`  a local, always-present id used to address a conversation in
 *            the UI. Never sent anywhere.
 *   - `id`   the backend session_id, which only exists once the backend has
 *            answered at least once. This is what /chat/stream and /reset
 *            receive.
 * Conflating them is what makes "new chat" accidentally append to an old
 * thread, so they stay separate.
 */

function newKey() {
  return `c_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function loadConversations() {
  try {
    const parsed = JSON.parse(localStorage.getItem(HISTORY_KEY));
    if (!Array.isArray(parsed)) return [];
    // Tolerate transcripts written by an older version of this app.
    return parsed.map((c) => ({ ...c, key: c.key || c.id || newKey() }));
  } catch {
    return [];
  }
}

function truncate(text, max) {
  return text.length <= max ? text : text.slice(0, max - 1) + "…";
}

export function useConversations() {
  const [conversations, setConversations] = useState(loadConversations);
  const [activeKey, setActiveKey] = useState(() => localStorage.getItem(ACTIVE_KEY));
  const [messages, setMessages] = useState(() => {
    const key = localStorage.getItem(ACTIVE_KEY);
    if (!key) return [];
    return loadConversations().find((c) => c.key === key)?.messages || [];
  });

  // Refs, not state, are what the callbacks read. A single turn calls
  // appendMessage twice (the user's message, then the assistant's) and the
  // second call happens inside an async closure captured before the first
  // one created the conversation. Reading `activeKey` from state there would
  // still see `null` and start a *second* conversation for the same turn, so
  // the current key is mirrored into a ref and updated synchronously.
  const conversationsRef = useRef(conversations);
  conversationsRef.current = conversations;

  const activeKeyRef = useRef(activeKey);

  const setActive = useCallback((key) => {
    activeKeyRef.current = key;
    setActiveKey(key);
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(conversations));
    } catch {
      // Storage can be full or blocked; the in-memory chat still works.
    }
  }, [conversations]);

  useEffect(() => {
    if (activeKey) localStorage.setItem(ACTIVE_KEY, activeKey);
    else localStorage.removeItem(ACTIVE_KEY);
  }, [activeKey]);

  const activeConversation = conversations.find((c) => c.key === activeKey) || null;
  const sessionId = activeConversation?.id || null;

  const appendMessage = useCallback(
    (role, text, backendSessionId, extra = {}) => {
      const message = { role, text, ...extra };
      setMessages((prev) => [...prev, message]);

      const current = activeKeyRef.current;
      const exists = conversationsRef.current.some((c) => c.key === current);
      const key = current && exists ? current : newKey();
      if (key !== current) setActive(key);

      setConversations((prev) => {
        const index = prev.findIndex((c) => c.key === key);

        if (index === -1) {
          return [
            {
              key,
              id: backendSessionId || null,
              title: role === "user" ? truncate(text, 42) : "New chat",
              timestamp: Date.now(),
              messages: [message],
            },
            ...prev,
          ];
        }

        const next = [...prev];
        const convo = { ...next[index] };
        convo.messages = [...convo.messages, message];
        convo.timestamp = Date.now();
        if (backendSessionId) convo.id = backendSessionId;
        if (convo.title === "New chat" && role === "user") convo.title = truncate(text, 42);
        next[index] = convo;
        return next;
      });
    },
    [setActive]
  );

  const loadConversation = useCallback(
    (key) => {
      const convo = conversationsRef.current.find((c) => c.key === key);
      if (!convo) return;
      setActive(key);
      setMessages(convo.messages);
    },
    [setActive]
  );

  const startNewConversation = useCallback(() => {
    setActive(null);
    setMessages([]);
  }, [setActive]);

  const deleteConversation = useCallback(
    async (key) => {
      const convo = conversationsRef.current.find((c) => c.key === key);
      if (convo?.id) {
        try {
          // Ask the backend to forget its in-memory state for that thread too.
          await resetConversation(convo.id);
        } catch {
          // Backend may be unreachable - still clear the local copy so the
          // UI stays consistent either way.
        }
      }
      setConversations((prev) => prev.filter((c) => c.key !== key));
      if (key === activeKeyRef.current) {
        setActive(null);
        setMessages([]);
      }
    },
    [setActive]
  );

  const deleteActiveConversation = useCallback(
    () => deleteConversation(activeKeyRef.current),
    [deleteConversation]
  );

  return {
    conversations: [...conversations].sort((a, b) => b.timestamp - a.timestamp),
    activeKey,
    sessionId,
    messages,
    appendMessage,
    loadConversation,
    startNewConversation,
    deleteConversation,
    deleteActiveConversation,
  };
}
