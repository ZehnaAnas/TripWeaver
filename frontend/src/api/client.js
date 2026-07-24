import axios from "axios";

// Point this at your deployed backend. Vite exposes build-time env vars
// prefixed with VITE_, read from a .env file or your hosting platform's
// environment variable settings.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Every message the user could ever see about a failure lives here, in the
// interface's own voice. Raw exceptions and stack traces never reach the UI.
const ERRORS = {
  unreachable:
    "I can't reach the travel assistant right now. Check that the backend is running at " +
    API_BASE_URL +
    ", then try again.",
  badResponse:
    "The travel assistant answered, but not with something I could read. Give it another try in a moment.",
  interrupted: "The connection dropped part-way through that answer. Try again.",
};

/**
 * Streaming chat deliberately uses the native fetch() API rather than axios -
 * browsers don't expose a reliable way to read a streaming response body
 * incrementally through axios's adapters, while fetch()'s
 * response.body.getReader() is the standard tool for this. Axios (via the
 * `api` instance above) is used for every other, non-streaming request.
 *
 * The backend speaks Server-Sent Events, so the reader buffers raw bytes and
 * splits on the blank-line delimiter - a single network chunk can carry half
 * an event or three whole ones.
 *
 * `signal` lets the caller abort mid-answer (the Stop button).
 */
export async function streamChat(message, sessionId, onEvent, signal) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
      signal,
    });
  } catch (err) {
    if (err?.name === "AbortError") return;
    onEvent({ type: "error", message: ERRORS.unreachable });
    return;
  }

  if (!response.ok || !response.body) {
    onEvent({ type: "error", message: ERRORS.badResponse });
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    let readResult;
    try {
      readResult = await reader.read();
    } catch (err) {
      if (err?.name === "AbortError") return;
      onEvent({ type: "error", message: ERRORS.interrupted });
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
        // A malformed event is skipped rather than killing the stream.
      }
    }
  }
}

export async function resetConversation(sessionId) {
  return api.post("/reset", { session_id: sessionId });
}
