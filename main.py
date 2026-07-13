from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from entity import ChatRequest, ChatResponse
from agents.graph import graph


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

        "hotel_search_cache": [],
        "flight_search_cache": [],

        "hotel_results": [],
        "flight_results": [],

        "response_text": ""
    }

conversation_state = create_empty_state()

@app.get("/")
async def hello():
    return {"message": "Hello World"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    # Add latest user message
    conversation_state["messages"].append(request.message)

    # Run graph
    result = await graph.ainvoke(conversation_state)

    # Save returned values back into the conversation state
    for key, value in result.items():
        conversation_state[key] = value

    response_text = conversation_state.get(
        "response_text",
        "Something went wrong."
    )

    # Save assistant reply so future prompts have chat history
    conversation_state["messages"].append(response_text)

    return ChatResponse(
        response=response_text,
        hotels=conversation_state.get("hotel_results") or None,
        flights=conversation_state.get("flight_results") or None,
    )


@app.post("/reset")
async def reset():
    global conversation_state
    conversation_state = create_empty_state()
    return {"message": "Conversation reset successfully."}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="localhost",
        port=8000
    )