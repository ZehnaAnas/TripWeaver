from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import uuid
import json
import asyncio
import re
import os
from entity import ChatRequest, ChatResponse,ResetRequest
from agents.graph import graph

print("checkpointer attached",graph.checkpointer)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str,dict] = {}

MAX_MESSSAGES = 20

NODE_ACTIVITY_STATUS = {
    "router":"ROUTING",
    "hotel_node":"SEARCHING",
    "flight_node":"SEARCHING",
    "weather_node":"SEARCHING",
    "places_node":"SEARCHING",
    "itinerary_node":"RESPONDING",
    "unknown_node":"RESPONDING",
    "generate_response":"RESPONDING",
}

NODE_LABELS = {
    "router":"Understanding your request...",
    "hotel_node": {
        "book":"Booking your hotel...",
        "default":"Searching hotel suggestions...",
    },
    "flight_node":{
        "book":"Booking your flight...",
        "default":"Searching flight options..."
    },
    "weather_node":"Checking the weather...",
    "places_node":"Finding things to do...",
    "itinerary_node":"Putting your itinerary together...",
    "unknown_node":"Thinking...",
    "generate_response":"Composing a response...",
}

def _node_status_event(node_name:str,accumalated_state:dict) -> dict:
    """Build the SSE 'status' event payload for a node that just finished."""
    label_entry = NODE_LABELS.get(node_name,"Working...")
    if isinstance(label_entry,dict):
        sub_action = accumalated_state.get("sub_action","default")
        label = label_entry.get(sub_action, label_entry["default"])
    else:
        label = label_entry
    
    return{
        "type":"status",
        "node":node_name,
        "activity_status":NODE_ACTIVITY_STATUS.get(node_name,"RESPONDING"),
        "label":label,
    }

def _sse(payload:dict)->str:
    """Format one Server-Sent-Events line"""
    return f"data: {json.dumps(payload)}\n\n"

def create_empty_state():
    return {
        "messages": [],
        "session_id":None,

        "intent": "",
        "sub_action": "",
        
        "activity_status": "ROUTING",
        "tool_status": "",

        "city": None,
        "city_code": None,
        "check_in": None,
        "check_out": None,

        "origin": None,
        "destination": None,
        "flight_date": None,

        "hotel_id": None,
        "flight_id": None,

        "star_rating": None,
        "hotel_budget": None,
        "flight_budget": None,

        "origin_country": None,
        "destination_country": None,
        "booking_confirmed": False,

        "passenger_email": None,
        "passenger_name":None,
        "flying_type": None,

        "guest_name": None,
        "guest_email": None,
        "room_type": None,

        "airline":None,
        "hotel_name":None,

        "hotel_search_cache": [],
        "flight_search_cache": [],

        "hotel_results": [],
        "flight_results": [],

        "response_text": "",
        
        "last_intent":None,
        "budget_adjustment":None,

        "weather_date":None,
        "weather_results":[],

        "activity_type":None,
        "activity_results":[],

        "activity_search_cache": [],
        "planned_activities": [],

        "awaiting_cancel_decision": False,
        "traveling_to_city": None,

    }

def get_session_state(session_id:str)-> dict:
    if session_id not in sessions:
        sessions[session_id] = create_empty_state()
    return sessions[session_id]

@app.get("/api/health")
async def hello():
    return {"message": "Hello World"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    state = get_session_state(session_id)
    state["session_id"] = session_id

    state["messages"].append(request.message)
    if len(state["messages"]) > MAX_MESSSAGES:
        state["messages"] = state["messages"][-MAX_MESSSAGES:]


    config = {"configurable": {"thread_id": session_id}}

    # Run graph
    result = await graph.ainvoke(state, config=config)

    # Save returned values back into the conversation state
    for key, value in result.items():
        state[key] = value

    response_text = state.get(
        "response_text",
        "Something went wrong."
    )
    # Save assistant reply so future prompts have chat history
    state["messages"].append(response_text)
    if len(state["messages"])>MAX_MESSSAGES:
        state["messages"] = state["messages"][-MAX_MESSSAGES:]
    
    sessions[session_id] = state
    return ChatResponse(
        response=response_text,
        session_id=session_id,
        hotels=state.get("hotel_results") or None,
        flights=state.get("flight_results") or None,
    )

@app.post("/chat/stream")
async def chat_stream(request:ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    state = get_session_state(session_id)
     
    state["messages"].append(request.message)
    if len(state["messages"]) > MAX_MESSSAGES:
        state["messages"] = state["messages"][-MAX_MESSSAGES:]

    # Same thread_id mapping as /chat above.
    config = {"configurable": {"thread_id": session_id}}

    async def event_generator():
        accumulated_state = dict(state)
        try:
            async for chunk in graph.astream(accumulated_state,stream_mode="updates",config=config):
                for node_name,partial_update in chunk.items():
                    accumulated_state.update(partial_update)
                    yield _sse(_node_status_event(node_name,accumulated_state))
        except Exception as e:
            yield _sse({
                "type":"error",
                "message":"Something went wrong while planning your trip. Please try again."
            })
            print(f"[chat_stream] graph error: {e}")
            return
         
        for key, value in accumulated_state.items():
            state[key] = value

        response_text = state.get("response_text") or "Something went wrong."

        # Save assistant reply so future prompts have chat history
        state["messages"].append(response_text)
        if len(state["messages"])>MAX_MESSSAGES:
            state["messages"] = state["messages"][-MAX_MESSSAGES:]
        sessions[session_id] = state

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
            "type":"done",
            "session_id":session_id,
            "hotels":state.get("hotel_results") or None,
            "flights": state.get("flight_results") or None
        })
    return StreamingResponse(event_generator(),media_type="text/event-stream")

@app.post("/reset")
async def reset(request:ResetRequest):
    if request.session_id in sessions:
        del sessions[request.session_id]

    try:
        await graph.checkpointer.adelete_thread(request.session_id)
    except Exception:
        pass

    return {"message":"Conversation reset successfully"}


_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )