from typing import Optional, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from .mcp_client import mcp_client
from .llm import llm
from .prompts import  get_system_prompt_for_unknown_node , get_system_prompt_with_history
from .entity import GraphState
from .mcp_utils import _parse_mcp_result,_extract_mcp_error
import traceback


class TravelExtraction(BaseModel):
    intent: Literal["hotel", "flight","weather","activities","transport","itinerary","unknown"] = Field(
        default="unknown",
        description= "Main user intent: hotel, flight, weather (forecast for a city), "
            "activities (things to do/attractions in a city), transport (local "
            "directions between two places), itinerary (combine a previously "
            "searched hotel and flight into one plan), or unknown."
    )

    sub_action: Literal["search", "list_all","book", "general"] = Field(
        default="general",
        description="Action type: search, list_all, book or general."
    )

    city: Optional[str] = Field(
        default=None,
        description="Hotel city name . Example: Mumbai, Colombo, Bangkok"
    )

    city_code: Optional[str] = Field(
        default=None,
        description="Hotel airport code. Example : BKK,CEB, SIN"
    )

    check_in: Optional[str] = Field(
        default=None,
        description="Hotel check-in date in YYYY-MM-DD format. Null if not provided."
    )

    check_out: Optional[str] = Field(
        default=None,
        description="Hotel check-out date in YYYY-MM-DD format. Null if not provided."
    )

    origin: Optional[str] = Field(
        default=None,
        description="Flight origin city or airport code. Example: BOM, CMB, Mumbai."
    )

    destination: Optional[str] = Field(
        default=None,
        description="Flight destination city or airport code. Example: DEL, BKK, Delhi."
    )

    flight_date: Optional[str] = Field(
        default=None,
        description="Flight date in YYYY-MM-DD format. Null if not provided."
    )


    star_rating : Optional[int] = Field(
        default = None,
        description="Star rating for flight booking. Null if not provided "
    )

    hotel_budget : Optional[int] = Field(
        default=None,
        description="Budget for searching hotels. Null if not provided"
    )

    flight_budget : Optional[int] = Field(
        default=None,
        description="Budget for searching flights. Null if not provided"
    )

    origin_country : Optional[str] = Field(
        default = None,
        description="Origin country for flight booking. Null if not provided"
    )

    destination_country : Optional[str] = Field(
        default = None,
        description="Destination country for flight booking. Null if not provided"
    )

    passenger_email: Optional[str]= Field(
        default = None,
        description= "Passengers email for flight booking. Null if not provided"
    )

    passenger_name: Optional[str] = Field(
        default = None,
        description = "Passengers name for flight booking. Null if not provided"
    )


    flying_type:Optional[str] = Field(
        default = None,
        description= "Flying type such as first class, business class, economy class. Null if not provided"
    )


    date_of_birth:Optional[str] = Field(
        default=None,
        description="Passengers date of birth for flight booking details. Null if not provided "
    )

    passport_number:Optional[str] = Field(
        default=None,
        description="Passport number of passengers for flight booking details. Null if not provided"
    )

    nationality:Optional[str] = Field(
        default=None,
        description="Passengers nationality for flight booking details. Null if not provided"

    )
    guest_name:Optional[str] = Field(
        default= None,
        description="Guests names for hotel booking details. Null if not provided"
    )
    guest_email:Optional[str] = Field(
        default = None,
        description="Guests emails for hotel booking details. Null if not provided"
    )

    room_type:Optional[str] = Field(
        default = None,
        description="Room type such as single, double or suite. Null if not provided"
    )

    hotel_name: Optional[str] = Field(
    default=None,
    description="Hotel name if user specifies one.Null if not provided"
    )

    airline: Optional[str] = Field(
        default=None,
        description="Airline such as Japan Airlines, Cathay Pacific"
    )

    weather_date: Optional[str] = Field(
        default = None,
        description= "Date for a weather forecast in YYYY-MM-DD format. Null if not provided - a general short outlook will be returned instead."
    )

    activity_type : Optional[str] = Field(
        default=None,
        description="Category of activity requested. One of: museums, attractions, nature, nightlife, art, historic. Null if not specified."
    )

    transport_from : Optional[str] = Field(
        default = None,
        description="Starting point for a local transport/directions request within a city, e.g. a hotel name or landmark. Null if not provided."
    )

    transport_to : Optional[str] = Field(
        default=None,
        description="Destination point for a local transport/directions request within a city. Null if not provided."
    )

    transport_mode : Optional[Literal["driving","walking","cycling"]] = Field(
        default = None,
        description="Mode of local transport requested. Null if not specified (defaults to driving)"
    )

    budget_adjustment : Optional[Literal["lower","higher"]] = Field(
        default=None,
        description=( "Set to 'lower' if the user wants cheaper options than a previous search "
            "(e.g. 'make it cheaper', 'anything less expensive'), or 'higher' for more "
            "premium options, WITHOUT giving an exact number. Null if the user gave an "
            "exact budget figure instead (that goes in hotel_budget/flight_budget) or "
            "didn't ask for a price change.")
    )

travel_extractor = llm.with_structured_output(TravelExtraction)


def router(state: GraphState) -> dict:
    user_message = state["messages"][-1]
    history_messages = state["messages"][:-1]

    system_prompt = get_system_prompt_with_history("\n".join(history_messages))

    invocation_messages = [SystemMessage(content=system_prompt)]
    for i in range(0, len(history_messages), 2):
        invocation_messages.append(HumanMessage(content=history_messages[i]))
        if i + 1 < len(history_messages):
            invocation_messages.append(AIMessage(content=history_messages[i + 1]))
    invocation_messages.append(HumanMessage(content=user_message))

    booking_confirmed_this_turn = user_message.lower() in ["yes","confirm","proceed"]
    try:
        extracted = travel_extractor.invoke(invocation_messages)
        data = extracted.dict()

    except Exception:
        data = {
            "intent": "unknown",
            "sub_action": "general",
            "city": None,
            "city_code":None,
            "check_in": None,
            "check_out": None,
            "origin": None,
            "destination": None,
            "flight_date": None,
            "hotel_id": None,
            "flight_id": None,
            "star_rating":None,
            "flight_budget":None,
            "hotel_budget":None,
            "origin_country":None,
            "destination_country":None,
            "passenger_email":None,
            "passenger_name":None,
            "flying_type":None,
            "date_of_birth":None,
            "passport_number":None,
            "nationality":None,
            "guest_name":None,
            "guest_email":None,
            "room_type":None,
            "airline":None,
            "hotel_name":None
        
        }

    resolved_intent = data.get("intent") or state.get("last_intent","unknown") 
    if resolved_intent == "unknown" and state.get("last_intent") in ("hotel","flight","weather","activities","transport"):
        resolved_intent = state["last_intent"]

    return {

    "intent": resolved_intent,
    "sub_action": data.get("sub_action") or state.get("sub_action","general"),
    "last_intent":resolved_intent if resolved_intent in ("hotel","flight","weather","activities","transport") else state.get("last_intent"),

    "city": data.get("city") or state.get("city"),
    "city_code": data.get("city_code") or state.get("city_code"),

    "check_in": data.get("check_in") or state.get("check_in"),
    "check_out": data.get("check_out") or state.get("check_out"),

    "origin": data.get("origin") or state.get("origin"),
    "destination": data.get("destination") or state.get("destination"),

    "flight_date": data.get("flight_date") or state.get("flight_date"),

    "hotel_id": state.get("hotel_id"),
    "flight_id": state.get("flight_id"),
    "booking_confirmed": booking_confirmed_this_turn or state.get("booking_confirmed", False),

    "hotel_budget": data.get("hotel_budget") or state.get("hotel_budget"),
    "flight_budget": data.get("flight_budget") or state.get("flight_budget"),
    "budget_adjustment":data.get("budget_adjustment"),

    "origin_country": data.get("origin_country") or state.get("origin_country"),
    "destination_country": data.get("destination_country") or state.get("destination_country"),
    "airline":data.get("airline") or state.get("airline"),

    "guest_name": data.get("guest_name") or state.get("guest_name"),
    "guest_email": data.get("guest_email") or state.get("guest_email"),

    "passenger_name": data.get("passenger_name") or state.get("passenger_name"),
    "passenger_email": data.get("passenger_email") or state.get("passenger_email"),

    "passport_number": data.get("passport_number") or state.get("passport_number"),
    "date_of_birth": data.get("date_of_birth") or state.get("date_of_birth"),
    "nationality": data.get("nationality") or state.get("nationality"),

    "room_type": data.get("room_type") or state.get("room_type"),
    "flying_type": data.get("flying_type") or state.get("flying_type"),
    "hotel_name": data.get("hotel_name") or state.get("hotel_name"),

    "weather_date": data.get("weather_date") or state.get("weather_date"),
    "activity_type": data.get("activity_type") or state.get("activity_type"),
    "transport_from": data.get("transport_from") or state.get("transport_from"),
    "transport_to": data.get("transport_to") or state.get("transport_to"),
    "transport_mode": data.get("transport_mode") or state.get("transport_mode"),

    "activity_status":"ROUTING",
    "tool_status": state.get("tool_status"),

    "hotel_results": [],
    "flight_results": [],
    "weather_results": [],
    "activity_results": [],
    "transport_results": [],
    "hotel_search_cache": state.get("hotel_search_cache", []),
    "flight_search_cache": state.get("flight_search_cache", []),

    "response_text": ""
}
    

def _format_hotel(hotel: dict) -> str:
    name = hotel.get("name", "Unknown hotel")

    city_data = hotel.get("city", "unknown city")
    if isinstance(city_data, dict):
        city = city_data.get("name", "unknown city")
    else:
        city = city_data

    stars = hotel.get("starRating", "N/A")
    price = hotel.get("price", hotel.get("pricePerNight", "N/A"))
    currency = hotel.get("currency", "USD")

    available = hotel.get(
        "available_rooms",
        hotel.get("availableRooms", hotel.get("available", "N/A"))
    )

    return (
        f"{name} in {city}, "
        f"{stars} stars - {currency} {price}/night - "
        f"{available} rooms"
    )


def _format_flight(flight: dict) -> str:
    airline = flight.get(
        "airline", 
        "Unknown airline"
        )
    
    origin = flight.get(
        "originAirport") or flight.get(
            "originCity",
            "unknown"
            )
    
    destination  = flight.get(
        "destinationAirport") or flight.get(
            "destinationCity",
            "unknown"
            )
    
    flight_date = flight.get(
        "flightDate",
        "unknown"
        )
    
    departure_time = flight.get(
        "departureTime",
        "N/A"
        )
    
    arrival_time = flight.get(
        "arrivalTime",
        "N/A"
        )
    
    price = flight.get(
        "price",
        "N/A"
        )
    
    currency = flight.get(
        "currency",
        "USD"
        )
    
    seats = flight.get(
        "availableSeats",
        "N/A"
        )
    
    number = flight.get(
        "flightNumber",
        flight.get("flight_number", flight.get("flightNo", "N/A"))
    )

    return (
        f"{airline} {number} from {origin} to {destination} "
        f"on {flight_date}, {departure_time} - {arrival_time} "
        f"- {currency} {price} - {seats} seats"
    )

def _format_weather_day(day:dict)->str:
    date = day.get("date","unknown date")
    condition = day.get("condition","N/A")
    high = day.get("high_c","N/A")
    low = day.get("low_c","N/A")
    return f"{date}:{condition},{low}-{high}\u00b0C"

def _format_activity(place:dict)->str:
    name = place.get("name","Unknown place")
    category = place.get("category","attraction")
    return f"{name} ({category})"

def _format_transport(route:dict)->str:
    origin = route.get("origin","unknown")
    destination = route.get("destination","unknown")
    mode = route.get("mode","driving")
    distance = route.get("distance_km","N/A")
    duration = route.get("duration_minutes","N/A")
    return f"{origin} \u2192 {destination} by {mode} : {distance} km, ~{duration} min"

async def hotel_node(state: GraphState) -> dict:
    try:
        message = state["messages"][-1].lower()
        resolved_hotel_id = state.get("hotel_id")
        cache = state.get("hotel_search_cache",[])
        if "first" in message and len(cache)>=1:
            resolved_hotel_id = cache[0]["hotelID"]
        elif "second" in message and len(cache)>=2:
            resolved_hotel_id = cache[1]["hotelID"]
        elif "third" in message and len(cache)>=3:
            resolved_hotel_id = cache[2]["hotelID"]
        else:
            for hotel in cache:
                if hotel.get("name") and hotel["name"].lower() in message:
                    resolved_hotel_id = hotel["hotelID"]

        adjusted_hotel_budget = state.get("hotel_budget")
        if state.get("budget_adjustment") == "lower" and adjusted_hotel_budget:
            adjusted_hotel_budget = max(1, int(adjusted_hotel_budget*0.7))
        elif state.get("budget_adjustment") == "higher" and adjusted_hotel_budget:
            adjusted_hotel_budget = int(adjusted_hotel_budget*1.3)
        if state["sub_action"] == "book":
                missing = []
                if not resolved_hotel_id:
                    missing.append("hotel ID")
                if not state["guest_name"]:
                    missing.append("guest name")
                if not state["guest_email"]:
                    missing.append("guest email")
                if not state["check_in"]:
                    missing.append("check-in date")
                if not state["check_out"]:
                    missing.append("check-out date")
                if not state["room_type"]:
                    missing.append("room type")
                if missing:
                    return{
                        "hotel_id":resolved_hotel_id,
                        "activity_status":"CLARIFYING",
                        "response_text":f"I need the following information before booking:\n"+"\n".join(missing)
                        }
                if not state.get("booking_confirmed"):
                    return {
                        "hotel_id":resolved_hotel_id,
                        "activity_status":"CLARIFYING",
                        "response_text":"Please confirm these booking details.\n\nReply with 'Yes' if you'd like me to complete the booking."
                    }
                
        async with mcp_client.session("hotel") as session:
            hotel_tools = await load_mcp_tools(session)
            agent = llm.bind_tools(hotel_tools)
            messages = [
                SystemMessage(content=(
                    "You are the hotel booking agent. "
                    "Use the available tools to search,list, or book hotels according to the user's input. "
                    "CRITICAL: for any request asking what hotels are available, searching, or listing hotels, "
                    "you MUST call search_hotel or list_all_hotels THIS turn, even if similar hotels were "
                    "discussed earlier in the conversation. Never answer a hotel availability question from "
                    "memory of earlier messages - always call the tool fresh, since only a fresh tool call "
                    "updates the system's hotel cache that later booking steps depend on. If the tool returns "
                    "no results, say so honestly instead of inventing hotel names, prices, or IDs. "
                    "If a city (or any other filter like budget or star rating) is mentioned, use search_hotel - "
                    "list_all_hotels takes no filters and returns hotels from every city, so only use it when the "
                    "user genuinely wants to browse everything with no city/budget/rating mentioned at all. "
                    "If the user has given an input about hotels but with mispellings, wrong formats and other errors, find similar flight information according to it and ask the user if it's correct ,if not ask them to try again"
                    "Never invent a hotel_id, it must come from a prior search or list result. "
                    "If required hotel booking details are missing, then ask the user for them instead of guessing"
                    "Before confirming the hotel booking , make sure to ask the user if the details are correct and if they agree to proceed with the booking. "
                    )),
                    *[HumanMessage(content=m) for m in state["messages"]],
            ]
            
            response = await agent.ainvoke(messages)
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                matching_tool = next(t for t in hotel_tools if t.name == tool_call["name"])
                args = dict(tool_call["args"])
                if tool_call["name"] == "book_hotel" and resolved_hotel_id:
                    args["hotel_id"] = resolved_hotel_id
                result = _parse_mcp_result(await matching_tool.ainvoke(args))
                error_message = _extract_mcp_error(result)
                if error_message:
                    return{
                        "hotel_id":resolved_hotel_id,
                        "hotel_results":[],
                        "flight_results":[],
                        "response_text":f"I couldn't complete that request - {error_message}"
                    }
                if isinstance(result,list):
                    return {
                        "hotel_id":resolved_hotel_id,
                        "hotel_budget":adjusted_hotel_budget,
                        "budget_adjustment":None,
                        "hotel_results":result,
                        "hotel_search_cache":result,
                        "flight_results":[],
                        "response_text":""
                    }
                
                return {
                "hotel_id":resolved_hotel_id,
                "booking_confirmed":False,
                "hotel_results":[],
                "flight_results":[],
                "response_text":str(result)
                }
            return {"hotel_id":resolved_hotel_id,"response_text":response.content}
    except Exception as e:
            traceback.print_exc()
            return {"hotel_results":[],"flight_results":[],"response_text":"The hotel booking service is currently unavailable. Please try again in a few moments or continue asking other travel questions."}

async def flight_node(state: GraphState) -> dict:
    try:
        message = state["messages"][-1].lower()
        resolved_flight_id = state.get("flight_id")
        cache = state.get("flight_search_cache", [])
        if "first" in message and len(cache) >= 1:
            resolved_flight_id = cache[0]["flightId"]
        elif "second" in message and len(cache) >= 2:
            resolved_flight_id = cache[1]["flightId"]
        elif "third" in message and len(cache) >= 3:
            resolved_flight_id = cache[2]["flightId"]

        adjusted_flight_budget = state.get("flight_budget")
        if state.get("budget_adjustment") == "lower" and adjusted_flight_budget:
            adjusted_flight_budget = max(1,int(adjusted_flight_budget*0.7))
        elif state.get("budget_adjustment") == "higher" and adjusted_flight_budget:
            adjusted_flight_budget = int(adjusted_flight_budget*1.3)

        if state.get("sub_action") == "book":
            missing = []
            if not resolved_flight_id:
                missing.append("flight ID")
            if not state.get("passenger_email"):
                missing.append("passenger email")
            if not state.get("passenger_name"):
                missing.append("passenger name")
            if not state.get("flying_type"):
                missing.append("flying type")
            if not state.get("date_of_birth"):
                missing.append("date of birth")
            if not state.get("passport_number"):
                missing.append("passport number")
            if not state.get("nationality"):
                missing.append("nationality")

            if missing:
                return {
                    "flight_id": resolved_flight_id,
                    "activity_status": "CLARIFYING",
                    "response_text": "I still need:\n" + "\n".join(missing),
                }

            if not state.get("booking_confirmed"):
                return {
                    "flight_id": resolved_flight_id,
                    "activity_status": "CLARIFYING",
                    "response_text": "Please confirm these booking details.\n\nReply with 'Yes' if you'd like me to complete the booking.",
                }

        async with mcp_client.session("flight") as session:
            flight_tools = await load_mcp_tools(session)
            agent = llm.bind_tools(flight_tools)

            messages = [
                SystemMessage(content=(
                    "You are the flight booking agent. "
                    "Use the available tools to list, search, or book flights according to the user's input. "
                    "CRITICAL: for any request asking what flights are available, searching, or listing flights, "
                    "you MUST call search_flights or get_all_flights THIS turn, even if similar flights were "
                    "discussed earlier in the conversation. Never answer a flight availability question from "
                    "memory of earlier messages - always call the tool fresh, since only a fresh tool call "
                    "updates the system's flight cache that later booking steps depend on. If the tool returns "
                    "no results, say so honestly instead of inventing airlines, prices, or IDs. "
                    "If the user has given an input about flights but with misspellings, wrong formats, or other "
                    "errors, find the closest matching flight information and ask the user to confirm it before "
                    "proceeding; if there's no reasonable match, ask them to try again. "
                    "Never invent a flight_id — it must come from a prior search or list result. "
                    "If required booking details are missing, ask the user for them instead of guessing. "
                    "Before confirming a booking, ask the user to confirm the details are correct."
                )),
                *[HumanMessage(content=m) for m in state["messages"]],
            ]

            response = await agent.ainvoke(messages)

            if response.tool_calls:
                tool_call = response.tool_calls[0]
                matching_tool = next(t for t in flight_tools if t.name == tool_call["name"])
                args = dict(tool_call["args"])
                if tool_call["name"] == "book_flight" and resolved_flight_id:
                    args["flight_id"] = resolved_flight_id
                if tool_call["name"] == "search_flights" and adjusted_flight_budget:
                    args["flight_budget"] = adjusted_flight_budget
                
                result = _parse_mcp_result(await matching_tool.ainvoke(args))
                error_message = _extract_mcp_error(result)

                if error_message:
                    return{
                        "flight_id":resolved_flight_id,
                        "hotel_results":[],
                        "flight_results":[],
                        "response_text":f"I couldn't complete that request-{error_message}"
                    }
                if isinstance(result, list):
                    return {
                        "flight_id": resolved_flight_id,
                        "flight_budget":adjusted_flight_budget,
                        "budget_adjustment":None,
                        "hotel_results": [],
                        "flight_results": result,
                        "flight_search_cache":result,
                        "response_text":"",
                        }
                return{
                    "flight_id":resolved_flight_id,
                    "booking_confirmed":False,
                    "hotel_results":[],
                    "flight_results":[],
                    "response_text":str(result),
                }

            return {"flight_id": resolved_flight_id, "response_text": response.content}

    except Exception:
        traceback.print_exc()
        return {
            "hotel_results": [], "flight_results": [],
            "response_text": "Flight search is temporarily unavailable — please try again shortly.",
        }
    
async def weather_node(state:GraphState)->dict:
    try:
        async with mcp_client.session("weather") as session:
            weather_tools = await load_mcp_tools(session)
            agent = llm.bind_tools(weather_tools)

            messages = [
                SystemMessage(content=(
                    "You are the weather agent. Use the available tool to get a forecast for the city the user is asking about"
                    "If no city is given, ask for one instead of guessing."
                )),
                *[HumanMessage(content=m) for m in state["messages"]]
            ]
            response = await agent.ainvoke(messages)
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                matching_tool = next(t for t in weather_tools if t.name == tool_call["name"])
                args = dict(tool_call["args"])
                raw_result = await matching_tool.ainvoke(args)
                result = _parse_mcp_result(raw_result)
                error_message = _extract_mcp_error(result)
                if error_message:
                    return{
                        "weather_results":[],
                        "response_text":f"I couldn't get the weather for that city - {error_message}"
                    }
                
                return{
                    "weather_results":[result] if isinstance(result,dict) else result,
                    "response_text": "",
                }
            return {"response_text":response.content}
    except Exception:
        traceback.print_exc()
        return {
            "weather_results":[],
            "response_text":"The weather service is currently unavailable. Please try again shortly."
        }
    
async def activities_node(state:GraphState)->dict:
    try:
        async with mcp_client.session("activities") as session:
            activity_tools = await load_mcp_tools(session)
            agent = llm.bind_tools(activity_tools)

            messages = [
                SystemMessage(content=(
                    "You are the activities agent."
                    "Use the available tool to find things to do in the city the user mentions"
                    "Supported categories:museums,attractions,nature,nightlife,art,historic."
                    "If no city is given, ask for one instead of guessing"
                )),
                *[HumanMessage(content=m) for m in state["messages"]],
            ]
            response = await agent.ainvoke(messages)
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                matching_tool = next(t for t in activity_tools if t.name == tool_call["name"])
                args = dict(tool_call["args"])
                raw_result = await matching_tool.ainvoke(args)
                result = _parse_mcp_result(raw_result)
                error_message = _extract_mcp_error(result)
                if error_message:
                    return {
                        "activity_results":[],
                        "response_text":f"I couldn't find activities for that city - {error_message}"
                    }
                return{
                    "activity_results":result if isinstance(result,list) else [],
                    "response_text":"",
                }
            return{"response_text":response.content}
    except Exception:
        traceback.print_exc()
        return {
            "activity_results":[],
            "response_text":"The activities service is currently unavailable. Please try again shortly."
        }
    
async def transport_node(state:GraphState)-> dict:
    try:
        async with mcp_client.session("transport") as session:
            transport_tools = await load_mcp_tools(session)
            agent = llm.bind_tools(transport_tools)

            messages = [
                SystemMessage(content=(
                    "You are the local transport agent. "
                    "Use the available tool to get directions between two places the user names (e.g. a hotel and an attraction)." \
                    "Supported modes: driving, walking, cycling (default driving)." \
                    "If either place is missing ask for it instead of guessing."
                )),
                *[HumanMessage(content=m) for m in state["messages"]],
            ]
            response = await agent.ainvoke(messages)

            if response.tool_calls:
                tool_call = response.tool_calls[0]
                matching_tool = next(t for t in transport_tools if t.name == tool_call["name"])
                args = dict(tool_call["args"])
                raw_result = await matching_tool.ainvoke(args)
                result = _parse_mcp_result(raw_result)
                error_message = _extract_mcp_error(result)
                if error_message:
                    return{
                        "transport_results":[],
                        "response_text":f"I couldn't find directions for that route {error_message}",
                    }
                return{
                    "transport_results":[result] if isinstance(result,dict) else result,
                    "response_text":"",
                }
            return{"response_text":response.content}
    except Exception:
        traceback.print_exc()
        return{
            "transport_results":[],
            "response_text":"The transport service is currently unavailable. Please try again shortly."
        }
    
def itinerary_node(state:GraphState)->dict:
    """
    Richer orchestration: combines the most recent hotel and flight search 
    results (already cached in shared state by hotel_node/flight_node) into
    a single itinerary, without needing a fresh MCP call of its own.
    """
    hotels = state.get("hotel_search_cache",[])
    flights = state.get("flight_search_cache",[])

    missing = []
    if not hotels:
        missing.append("a hotel search")
    if not flights:
        missing.append("a flight search")
    if missing:
        return{
            "hotel_results":[], "flight_results":[],
            "response_text":(
                f"I need {'and'.join(missing)} first before I can put together an itinerary."
                "Try searching for a hotel and a flight, then ask me to combine them."
            )
        }
    top_flight = flights[0]
    top_hotel = hotels[0]

    lines = [
        "Here's a combined itinerary based on your most recent searches:\n",
        "Flight:",
        _format_flight(top_flight),
        "\nHotel:",
        _format_hotel(top_hotel)
    ]
    return {
        "hotel_results":[top_hotel],
        "flight_results":[top_flight],
        "response_text":"\n".join(lines),
    }

def unknown_node(state: GraphState) -> dict:
    user_message = state["messages"][-1]
    history_messages = state["messages"][:-1]

    system_prompt = get_system_prompt_for_unknown_node("\n".join(history_messages))

    invocation_messages = [SystemMessage(content=system_prompt)]
    for i in range(0, len(history_messages), 2):
        invocation_messages.append(HumanMessage(content=history_messages[i]))
        if i + 1 < len(history_messages):
            invocation_messages.append(AIMessage(content=history_messages[i + 1]))
    invocation_messages.append(HumanMessage(content=user_message))

    try:
        response = llm.invoke(invocation_messages)

        return {
            "hotel_results": [],
            "flight_results": [],
            "response_text": response.content,
        }

    except Exception as e:
        return {
            "hotel_results": [],
            "flight_results": [],
            "response_text": f"I couldn't understand your request clearly. Error: {str(e)}",
        }



def generate_response(state: GraphState) -> dict:
    if state.get("response_text") is not None and state["response_text"] != "":
        return {
            "response_text": state["response_text"]
        }

    hotel_results = state.get("hotel_results", [])
    flight_results = state.get("flight_results", [])
    weather_results = state.get("weather_results",[])
    activity_results = state.get("activity_results")
    transport_results = state.get("transport_results",[])

    if hotel_results:
        count = len(hotel_results)
        lines = [_format_hotel(hotel) for hotel in hotel_results[:5]]

        return {
            "response_text": (
                f"I found {count} hotel option{'s' if count != 1 else ''}:\n"
                + "\n".join(lines)
            )
        }

    if flight_results:
        count = len(flight_results)
        lines = [_format_flight(flight) for flight in flight_results[:5]]

        return {
            "response_text": (
                f"I found {count} flight option{'s' if count != 1 else ''}:\n"
                + "\n".join(lines)
            )
        }
    
    if weather_results:
        forecast = weather_results[0].get("forecast",[]) if isinstance(weather_results[0],dict) else []
        city = weather_results[0].get("city","that city") if isinstance(weather_results[0],dict) else "that city"
        lines = [_format_weather_day(day) for day in forecast[:5]]
        return{
            "response_text":f"Weather for {city}:\n"+"\n".join(lines)
        }
    
    if activity_results:
        count = len(activity_results)
        lines = [_format_activity(place) for place in activity_results[:8]]
        return{
            "response_text":(
                f"I found {count} thing {'s' if count !=1 else ''} to do:\n"
                +"\n".join(lines)
            )
        }
    if transport_results:
        lines = [_format_transport(route) for route in transport_results[:1]]
        return {"response_text":"\n".join(lines)}
    return {
        "response_text": "I couldn't find matching travel options."
    }


def route_after_extraction(state: GraphState) -> str:
    intent = state.get("intent", "unknown")

    if intent in ("hotel","flight","weather","activities","transport","itinerary"):
        return intent
    
    return "unknown"