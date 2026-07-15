from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uuid
import json
import asyncio
import re
from entity import ChatRequest, ChatResponse,ResetRequest
from agents.graph import graph


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
    "activities_node":"SEARCHING",
    "transport_node":"SEARCHING",
    "itinerary_node":"RESPONDING",
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
    "activities_node":"Finding things to do...",
    "transport_node":"Working out local directions...",
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
       
        "date_of_birth": None,
        "passport_number": None,
        "nationality":None,

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

        "transport_from":None,
        "transport_to":None,
        "transport_mode":None,
        "transport_results":[]
    }

def get_session_state(session_id:str)-> dict:
    if session_id not in sessions:
        sessions[session_id] = create_empty_state()
    return sessions[session_id]

@app.get("/")
async def hello():
    return {"message": "Hello World"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    state = get_session_state(session_id)

    state["messages"].append(request.message)
    if len(state["messages"]) > MAX_MESSSAGES:
        state["messages"] = state["messages"][-MAX_MESSSAGES:]

    # Run graph
    result = await graph.ainvoke(state)

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

    async def event_generator():
        accumulated_state = dict(state)
        try:
            async for chunk in graph.astream(accumulated_state,stream_mode="updates"):
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

        for piece in re.split(r"(\s+)",response_text):
            if piece == "":
                continue
            yield _sse({"type":"token","text":piece})
            await asyncio.sleep(0.03)
        yield _sse({
            "type":"done",
            "session_id":session_id,
            "hotels":state.get("hotel_results") or None,
            "flights": state.get("flight_results") or None
        })
    return StreamingResponse(event_generator(),media_type="text/event-stream")

@app.post("/reset")
async def reset(request:ChatRequest):
    if request.session_id in sessions:
        del sessions[request.session_id]
    return {"message":"Conversation reset successfully"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="localhost",
        port=8000
    )