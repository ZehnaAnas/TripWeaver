from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
import uuid
import json
import asyncio
import re
import os
from entity import ChatRequest, ChatResponse, ResetRequest
from agents.graph import graph


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NODE_ACTIVITY_STATUS = {
    "router": "ROUTING",
    "hotel_node": "SEARCHING",
    "flight_node": "SEARCHING",
    "activity_node": "SEARCHING",
    "unknown_node": "RESPONDING",
    "finalize_answer": "RESPONDING",
}

NODE_LABELS = {
    "router": "Understanding your request...",
    "hotel_node": "Working on your hotel request...",
    "flight_node": "Working on your flight request...",
    "activity_node": "Finding things to do...",
    "unknown_node": "Thinking...",
    "finalize_answer": "Composing a response...",
}


def _node_status_event(node_name: str) -> dict:
    return {
        "type": "status",
        "node": node_name,
        "activity_status": NODE_ACTIVITY_STATUS.get(node_name, "RESPONDING"),
        "label": NODE_LABELS.get(node_name, "Working..."),
    }


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@app.get("/api/health")
async def hello():
    return {"message": "Hello World"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=request.message)], "session_id": session_id},
        config=config,
    )

    response_text = result.get("response_text") or "Something went wrong."

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        hotels=result.get("hotel_results") or None,
        flights=result.get("flight_results") or None,
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    async def event_generator():
        accumulated_state = {}
        try:
            async for chunk in graph.astream(
                {"messages": [HumanMessage(content=request.message)], "session_id": session_id},
                stream_mode="updates",
                config=config,
            ):
                for node_name, partial_update in chunk.items():
                    accumulated_state.update(partial_update)
                    yield _sse(_node_status_event(node_name))
        except Exception as e:
            yield _sse({
                "type": "error",
                "message": "Something went wrong while planning your trip. Please try again.",
            })
            print(f"[chat_stream] graph error: {e}")
            return

        response_text = accumulated_state.get("response_text") or "Something went wrong."

        MAX_DELAYED_CHARS = 800
        TOKEN_DELAY_SECONDS = 0.015

        chars_sent = 0
        pieces = re.split(r"(\s+)", response_text)
        for i, piece in enumerate(pieces):
            if piece == "":
                continue
            if chars_sent < MAX_DELAYED_CHARS:
                yield _sse({"type": "token", "text": piece})
                chars_sent += len(piece)
                await asyncio.sleep(TOKEN_DELAY_SECONDS)
            else:
                remainder = "".join(pieces[i:])
                if remainder:
                    yield _sse({"type": "token", "text": remainder})
                break

        yield _sse({
            "type": "done",
            "session_id": session_id,
            "hotels": accumulated_state.get("hotel_results") or None,
            "flights": accumulated_state.get("flight_results") or None,
        })

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/reset")
async def reset(request: ResetRequest):
    try:
        await graph.checkpointer.adelete_thread(request.session_id)
    except Exception:
        pass
    return {"message": "Conversation reset successfully"}


_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)