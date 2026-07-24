# TripWeaver

An MCP-based multi-agent travel planner. You describe a trip in plain language;
a LangGraph router reads your intent and hands the turn to a specialist agent
for hotels, flights, activities or general travel questions. Those agents reach
every external service through MCP servers, never through API calls written
into the agent code.

- **Backend / agents** — Python, FastAPI, LangChain, LangGraph
- **Frontend** — React 19, Vite, Tailwind CSS v4
- **External services** — three MCP servers over streamable HTTP

---

## Contents

1. [Quick start](#1-quick-start)
2. [Environment variables](#2-environment-variables)
3. [MCP server setup guide](#3-mcp-server-setup-guide)
4. [Running in development](#4-running-in-development)
5. [Deployment](#5-deployment)
6. [User guide](#6-user-guide)
7. [How it works](#7-how-it-works)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Quick start

Requirements: Python 3.11+, Node.js 18+, an OpenAI API key, a Tavily API key.

```bash
git clone <your-repo-url>
cd TripWeaver1

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then fill in your keys

cd frontend && npm install && cd ..

python start_all.py               # starts all four processes
```

Open **http://localhost:8000**.

`start_all.py` launches the three MCP servers and the FastAPI backend, and
tears them all down on Ctrl+C. FastAPI serves the built frontend at `/`, so if
`frontend/dist` exists you get the whole app on one port.

---

## 2. Environment variables

Everything configurable lives in `.env`, which is listed in `.gitignore` and is
never committed. `.env.example` is the committed template.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | yes | — | The app raises a clear error at startup if this is missing. |
| `TAVILY_API_KEY` | yes | — | Used by the activities MCP server for live search. |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | Any chat-capable OpenAI model. |
| `HOTEL_MCP_URL` | no | `http://localhost:8001/mcp` | Where the backend reaches the hotel MCP server. |
| `FLIGHT_MCP_URL` | no | `http://localhost:8002/mcp` | Flight MCP server. |
| `ACTIVITY_MCP_URL` | no | `http://localhost:8003/mcp` | Activities MCP server. |
| `HOTEL_MCP_PORT` | no | `8001` | Port the hotel server binds to. |
| `FLIGHT_MCP_PORT` | no | `8002` | Port the flight server binds to. |
| `ACTIVITY_MCP_PORT` | no | `8003` | Port the activities server binds to. |
| `PORT` | no | `8000` | FastAPI port. Most hosts inject this. |
| `VITE_API_BASE_URL` | no | `http://localhost:8000` | Frontend only. Leave **empty** in production so the browser calls the same origin it was served from. |

Vite inlines `VITE_*` variables at **build** time, so changing one means
re-running `npm run dev` or `npm run build`.

---

## 3. MCP server setup guide

### What the servers expose

Each server is a standalone FastMCP process speaking streamable HTTP. The
backend discovers their tools at startup and caches them for the life of the
process.

| Server | Port | Tools |
| --- | --- | --- |
| `mcp_servers/hotel_server.py` | 8001 | `list_all_hotels`, `search_hotel`, `book_hotel` |
| `mcp_servers/flight_server.py` | 8002 | `get_all_flights`, `search_flights`, `book_flight` |
| `mcp_servers/activity_server.py` | 8003 | `search_activities`, `get_activity_details` |

Every tool carries a docstring, because FastMCP turns the docstring into the
tool description the model reads. A tool without one is effectively invisible
to the agent.

### Running them

Together, via the launcher:

```bash
python start_all.py
```

Or individually, one terminal each — useful when you want to watch a single
server's logs:

```bash
python mcp_servers/hotel_server.py       # :8001
python mcp_servers/flight_server.py      # :8002
python mcp_servers/activity_server.py    # :8003
python main.py                           # :8000
```

### Checking a server is up

```bash
curl -i http://localhost:8001/mcp
```

A live server answers on that path. A connection refused means it isn't
running; check the terminal it was launched from.

### Adding a new MCP server

Adding a service must not require touching agent code. The steps:

1. Write `mcp_servers/<name>_server.py` with `FastMCP("<Name> Service", port=800X)`
   and one `@mcp.tool()` per capability. Give every tool a real docstring.
2. End the file with `mcp.run(transport="streamable-http")`.
3. Register the URL in `agents/mcp_client.py`.
4. Add it to the `services` list in `start_all.py`.

A node picks the tools up with `await get_tools("<name>")`. No tool logic is
written into the agents themselves.

### Session lifetime — worth knowing

`get_tools()` in `agents/mcp_client.py` caches the tool objects once per
process. Each individual tool *call* opens its own short-lived MCP session.

This matters. An earlier version opened a session inside each node and held it
open across the whole agent run. That session is an anyio task group, and under
the streaming endpoint its cancel scope could be exited from a different task
than it entered in, which stalled the response. Process-scoped tools, request-
scoped calls — that is the rule.

---

## 4. Running in development

Two terminals, with the frontend on Vite's dev server for hot reload:

```bash
# terminal 1 - MCP servers + backend
python start_all.py

# terminal 2 - frontend with hot reload
cd frontend
npm run dev
```

Frontend at **http://localhost:5173**, backend at **http://localhost:8000**.
Set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env` for this mode.

Useful commands:

```bash
cd frontend && npm run build     # production bundle into frontend/dist
cd frontend && npm run lint      # oxlint
```

---

## 5. Deployment

Backend and frontend are deployed as two services.

**Backend — Render (or any Python host)**

| Setting | Value |
| --- | --- |
| Runtime | Python 3 |
| Build command | `pip install -r requirements.txt` |
| Start command | `python start_all.py` |
| Environment | `OPENAI_API_KEY`, `TAVILY_API_KEY` |

One instance runs all four processes. The three MCP servers stay on internal
localhost and are never exposed publicly; only the FastAPI port is, and the
host injects it as `PORT`. Because they share a network namespace, the default
MCP URLs are correct in production and need no override.

**Frontend — Vercel (or Netlify)**

| Setting | Value |
| --- | --- |
| Root directory | `frontend` |
| Framework | Vite (auto-detected) |
| Environment | `VITE_API_BASE_URL` = the backend URL |

Vite inlines `VITE_*` at build time, so changing the backend URL needs a
redeploy, not just a restart.

**Live URLs**

- Frontend: <your-vercel-url>
- Backend: <your-render-url>

**Deployment checklist**

- [ ] `.env` is gitignored and absent from history — `git log --all -- .env`
- [ ] Keys set in both dashboards, not in any committed file
- [ ] `/api/health` responds on the backend URL
- [ ] One hotel search and one flight search work through the deployed UI

## 6. User guide

Open the app and type in plain language. You never name an agent — the router
works out which specialist should handle the turn.

**Finding somewhere to stay**

> Find hotels in Bangkok under $120 a night

Results come back as a formatted list. Follow-ups keep their context, so
"anything cheaper?" or "the second one" work without repeating yourself.

**Booking**

> Book the first hotel

The agent asks only for what it doesn't already have — check-in, check-out,
guest name, email, room type. Answer in one line if you like:

> 2026-05-04,2026-05-06,Zehna,zehna@example.com,single

It books immediately and replies with the confirmation reference. There is no
separate "are you sure?" step; supplying the details is the confirmation.

**Flights**

> Find flights from Singapore to Kuala Lumpur

City names and three-letter airport codes both work. Booking needs a passenger
name and email.

**Things to do**

> What's worth seeing in Tokyo over three days?

**Interface**

- The status board above the input shows the live activity state — `ROUTING`
  while intent is being read, `SEARCHING` or `BOOKING` while an agent works,
  `RESPONDING` while the answer streams in. Completed steps stay on screen as
  ticks so you can see the route the request took.
- Replies stream word by word. **Stop** cancels mid-answer and keeps what
  arrived.
- **Copy plan** appears under any reply.
- The clock icon opens chat history; conversations survive a page reload.
- The sun/moon icon toggles light and dark.
- If a service is down you get a plain-language message and a **Try again**
  button, never a stack trace.

---

## 7. How it works

```
Browser (React)
     │  POST /chat/stream          Server-Sent Events
     ▼
FastAPI (main.py)
     │
     ▼
LangGraph StateGraph  ── router ──┬── hotel_node     ──┐
                                  ├── flight_node    ──┤
                                  ├── activity_node  ──┼── finalize_answer ──► END
                                  └── unknown_node   ──┘
                                          │
                                     MCP tools
                                          │
                    hotel :8001   flight :8002   activities :8003
                                          │
                                  external travel APIs
```

**Routing by intent.** `router` runs a structured-output extraction over the
conversation and returns `intent` plus `sub_action` (`search` / `list_all` /
`book`). A conditional edge dispatches to the specialist. Every key a node
returns must be declared in `GraphState` — LangGraph silently discards anything
that isn't, which is why `sub_action` appears there explicitly.

**State.** `agents/entity.py` is the single source of truth. `messages` uses
`add_messages` and is persisted by an `InMemorySaver` checkpointer keyed on
`session_id`. `finalize_answer` is the graph's only exit node, so it appends
the assistant's reply to `messages` there — once, and exactly the text the user
saw. Search results persist in `hotel_results` / `flight_results`, which is how
"book the second one" resolves on a later turn.

**Streaming and activity.** `/chat/stream` iterates `graph.astream(...,
stream_mode="updates")`. Each completed node emits a `status` event carrying its
activity state and label; the finalized answer is then emitted as `token`
events, and a `done` event closes the turn. The frontend renders tokens as they
arrive.

**Failure handling.** Every node wraps its work in `try/except` and returns a
readable `response_text` on failure, so one dead service degrades that agent
without taking down the conversation. MCP tool results are checked for error
payloads before being treated as data. No exception text reaches the user.

### Project layout

```
main.py                     FastAPI app: /chat, /chat/stream, /reset, static frontend
entity.py                   Request/response models
start_all.py                Launches all four processes
agents/
  graph.py                  StateGraph wiring and checkpointer
  entity.py                 GraphState schema
  nodes.py                  router, specialists, finalizer
  prompts.py                System prompts
  llm.py                    Model init and API-key validation
  mcp_client.py             MCP endpoints + cached tool loading
  mcp_utils.py              MCP error extraction
mcp_servers/
  hotel_server.py           :8001
  flight_server.py          :8002
  activity_server.py        :8003
  cache.py                  Optional Redis cache, in-memory fallback
frontend/
  src/App.jsx               Turn orchestration
  src/api/client.js         SSE reader, user-facing error copy
  src/hooks/                Conversation history, theme
  src/components/           Chat UI
```

---

## 8. Troubleshooting

**`OPENAI_API_KEY is not set`** — `.env` is missing or in the wrong folder. It
belongs in the project root, beside `main.py`.

**A search returns nothing at all** — the matching MCP server probably isn't
running. Check with `curl -i http://localhost:8001/mcp`.

**"The hotel booking service is currently unavailable"** — the node caught an
exception. The full traceback is in the backend terminal.

**Follow-ups behave like a new conversation** — the frontend sends `session_id`
with every request and the backend keys its checkpoint on it. Starting a new
chat deliberately clears it.

**Port already in use** — a previous run didn't shut down. Kill the stray
process or change the port via `HOTEL_MCP_PORT` / `FLIGHT_MCP_PORT` /
`ACTIVITY_MCP_PORT`.

**Frontend can't reach the backend** — in development, `frontend/.env` needs
`VITE_API_BASE_URL=http://localhost:8000`, and Vite must be restarted after
changing it.