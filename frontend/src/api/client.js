import axios from "axios";

// Point this at your deployed backend. Vite exposes build-time env vars
// prefixed with VITE_, read from a .env file or your hosting platform's
// environment variable settings.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Streaming chat deliberately uses the native fetch() API rather than
// axios - browsers don't expose a reliable way to read a streaming
// response body incrementally through axios's adapters, while
// fetch()'s response.body.getReader() is the standard, correct tool
// for this. Axios (via the `api` instance above) is used for every
// other, non-streaming request in this app.
export async function streamChat(message, sessionId, onEvent) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
  } catch {
    onEvent({
      type: "error",
      message: "I couldn't reach the travel assistant. Make sure the backend is running and reachable.",
    });
    return;
  }

  if (!response.ok || !response.body) {
    onEvent({
      type: "error",
      message: "I couldn't reach the travel assistant. Please try again in a moment.",
    });
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    let readResult;
    try {
      readResult = await reader.read();
    } catch {
      onEvent({ type: "error", message: "The connection was interrupted. Please try again." });
      return;
    }
    const { value, done } = readResult;
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      if (!rawEvent.startsWith("data: ")) continue;
      try {
        onEvent(JSON.parse(rawEvent.slice("data: ".length)));
      } catch {
        // malformed event - skip rather than crash the stream
      }
    }
  }
}

export async function resetConversation(sessionId) {
  return api.post("/reset", { session_id: sessionId });
}
