# TripWeaver — Chat Frontend

React + Vite + Tailwind CSS v4 frontend for the TripWeaver multi-agent travel
planner. It talks to the FastAPI backend over Server-Sent Events and renders the
agents' replies as they are generated.

---

## Requirements

- Node.js 18+
- The TripWeaver backend running (default `http://localhost:8000`)
- The three MCP servers running (hotel `:8001`, flight `:8002`, activities `:8003`)

## Setup

```bash
cd frontend
npm install
```

Create a `.env` in this folder (copy `.env.example`):

```
VITE_API_BASE_URL=http://localhost:8000
```

Vite only exposes variables prefixed with `VITE_`, and it inlines them at
**build** time — so after changing this you must restart `npm run dev` or
re-run `npm run build`.

## Running

**Development** (hot reload, frontend and backend on separate ports):

```bash
npm run dev          # http://localhost:5173
```

**Production build** (single origin — `main.py` mounts `frontend/dist` at `/`):

```bash
npm run build        # writes ./dist
cd .. && python main.py   # everything served from http://localhost:8000
```

`npm run lint` runs oxlint over `src/`.

---

## How it fits together

| File | Responsibility |
| --- | --- |
| `src/App.jsx` | Turn orchestration: send, stream, stop, retry, error handling |
| `src/api/client.js` | SSE reader for `/chat/stream`, axios for `/reset`, all user-facing error copy |
| `src/hooks/useConversations.js` | Transcript history in localStorage; keeps local key and backend `session_id` separate |
| `src/hooks/useTheme.js` | Light/dark class on `<html>`, persisted |
| `src/components/ActivityBoard.jsx` | Agent-activity visualisation (the lifecycle from SRS §6) |
| `src/components/ChatMessage.jsx` | User / assistant / error message variants, copy button |
| `src/components/Markdown.jsx` | Renders the finalizer agent's Markdown output |
| `src/components/QuickReplies.jsx` | Follow-up suggestions based on what the turn produced |
| `src/index.css` | Design tokens; light values in `@theme`, dark overrides in `html.dark` |

### Streaming

`/chat/stream` returns `text/event-stream`. `streamChat()` reads the response
body with `response.body.getReader()` — axios cannot read a body
incrementally, which is why this one call uses `fetch` while everything else
uses axios. A single network chunk may contain half an event or several, so
bytes are buffered and split on the blank-line delimiter before being parsed.

Four event types are handled:

| Event | Effect |
| --- | --- |
| `status` | Appends a step to the activity board (`ROUTING`, `SEARCHING`, …) |
| `token` | Appended to React state immediately, so text renders word by word |
| `done` | Records the `session_id` and whether the turn produced hotel/flight results |
| `error` | Renders the error message variant with a Try again action |

An `AbortController` backs the Stop button; text already streamed is kept.

### Theming

All colours are CSS custom properties. `@theme` in `index.css` holds the light
values, `html.dark` overrides the same names, and every utility
(`bg-canvas`, `text-ink`, `border-line`, …) resolves through `var()`. Flipping
one class on `<html>` re-themes the whole app — there are no `dark:` variants
scattered through the components. An inline script in `index.html` applies the
saved or system preference before first paint so the page never flashes.

### Errors

No raw exception ever reaches the screen. Network failures, non-OK responses
and dropped connections each map to a sentence written in the interface's
voice, defined in one place at the top of `src/api/client.js`.
