from typing import Optional, Literal

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from .mcp_client import mcp_client
from .llm import llm
from .prompts import get_system_prompt_for_unknown_node, get_system_prompt_with_history
from .entity import GraphState
from .mcp_utils import _parse_mcp_result
import traceback


class TravelExtraction(BaseModel):
    intent: Literal["hotel", "flight", "unknown"] = Field(
        default="unknown",
        description="Main user intent: hotel, flight, or unknown."
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

    hotel_id: Optional[str] = Field(
        default=None,
        description="hotel ID for hotel booking. Null if not provided."
    )

    flight_id: Optional[str] = Field(
        default=None,
        description="flight ID for flight booking. Null if not provided."
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

    if user_message.lower() in ["yes", "confirm", "proceed"]:
        state["booking_confirmed"] = True
    try:
        state["activity_status"] = "ROUTING"
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

    return {

    "intent": data.get("intent") or state.get("intent","unknown"),
    "sub_action": data.get("sub_action") or state.get("sub_action","general"),

    "city": data.get("city") or state.get("city"),
    "city_code": data.get("city_code") or state.get("city_code"),

    "check_in": data.get("check_in") or state.get("check_in"),
    "check_out": data.get("check_out") or state.get("check_out"),

    "origin": data.get("origin") or state.get("origin"),
    "destination": data.get("destination") or state.get("destination"),

    "flight_date": data.get("flight_date") or state.get("flight_date"),

    "hotel_id": data.get("hotel_id") or state.get("hotel_id"),
    "flight_id": data.get("flight_id") or state.get("flight_id"),
    "booking_confirmed": state.get("booking_confirmed", False),

    "hotel_budget": data.get("hotel_budget") or state.get("hotel_budget"),
    "flight_budget": data.get("flight_budget") or state.get("flight_budget"),

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

    "activity_status": state.get("activity_status"),
    "tool_status": state.get("tool_status"),

    "hotel_results": state.get("hotel_results", []),
    "flight_results": state.get("flight_results", []),
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



async def hotel_node(state: GraphState) -> dict:
    try:
        async with mcp_client.session("hotel") as session:
            hotel_tools = await load_mcp_tools(session)
            state["activity_status"] = "SEARCHING"
            state["tool_status"] = "INVOKED"
            agent = llm.bind_tools(hotel_tools)
            state["tool_status"] = "SUCCEEDED"
            state["activity_status"] = "RESPONDING"
            messages = [
                SystemMessage(content=(
                    "You are the hotel booking agent. "
                    "Use the available tools to search,list, or book hotels according to the user's input. "
                    "If the user has given an input about hotels but with mispellings, wrong formats and other errors, find similar flight information according to it and ask the user if it's correct ,if not ask them to try again"
                    "Never invent a hotel_id, it must come from a prior search or list result. "
                    "If required hotel booking details are missing, then ask the user for them instead of guessing"
                    "Before confirming the hotel booking , make sure to ask the user if the details are correct and if they agree to proceed with the booking. "
                    )),
                    *[HumanMessage(content=m) for m in state["messages"]],
            ]
            message = state["messages"][-1].lower()
            if "first" in message and state["hotel_search_cache"]:
                state["hotel_id"] = state["hotel_search_cache"][0]["hotelID"]
            elif "second" in message  and len(state["hotel_search_cache"])>=1:
                state["hotel_id"] = state["hotel_search_cache"][1]["hotelID"]
            elif "third" in message and len(state["hotel_search_cache"]) >= 2:
                state["hotel_id"] = state["hotel_search_cache"][2]["hotelID"]
            if state["sub_action"] == "book":
                state["activity_status"] = "BOOKING"
                missing = []
                if not state["hotel_id"]:
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
                    state["activity_status"] = "CLARIFYING"
                    return{
                        "response_text":
                        f"I need the following information before booking:\n"
                        +"\n".join(missing)
                        }
                if not state.get("booking_confirmed"):
                    return {
                        "response_text":
                        (
                            "Please confirm these booking details.\n\n"
                            "Reply with 'Yes' if you'd like me to complete the booking."
                        )
                            }
            response = await agent.ainvoke(messages)
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                matching_tool = next(t for t in hotel_tools if t.name == tool_call["name"])
                result = _parse_mcp_result(await matching_tool.ainvoke(tool_call["args"]))
                if isinstance(result,list):
                    if result and isinstance(result[0], dict) and result[0].get("error"):
                        return {
                            "response_text": result[0]["message"],
                            "flight_results": [],
                            "hotel_results": []
                            }
                    return {
                    "hotel_results":result,
                    "hotel_search_cache":result,
                    "flight_results":[],
                    "response_text":""
                    }
                if isinstance(result,dict) and result.get("error"):
                    return {"hotel_results":[],"flight_results":[],"response_text":"I couldn't complete that request- the hotel service returned an error. Please try again or rephrase your search"}
                return {
                "hotel_results":[],
                "flight_results":[],
                "response_text":str(result)
                }
            return {"response_text":response.content}
    except Exception as e:
            traceback.print_exc()
            return {"hotel_results":[],"flight_results":[],"response_text":"The hotel booking service is currently unavailable. Please try again in a few moments or continue asking other travel questions."}

async def flight_node(state: GraphState) -> dict:
    try:
        async with mcp_client.session("flight") as session:
            flight_tools = await load_mcp_tools(session)
            state["activity_status"] = "SEARCHING"
            state["tool_status"] = "INVOKED"
            agent = llm.bind_tools(flight_tools)
            messages = [
                SystemMessage(content=(
                    "You are the flight booking agent."
                    "Use the available tools to list,search or book flights according to the user's input."
                    "If the user has given an input about flights but with mispellings, wrong formats and other errors, find similar flight information according to it and ask the user if it's correct ,if not ask them to try again"
                    "Never invent the flight_id, ensure it comes from a prior list or search result."
                    "If required flight booking details are missing , then ask the user for it instead of guessing them"
                    "Before confirming the flight booking , make sure to ask the user if the details are correct and if they agree to proceed with the booking"
                )),
                *[HumanMessage(content=m) for m in state["messages"]],
            ]
            state["tool_status"] = "SUCCEEDED"
            state["activity_status"] = "RESPONDING"
            message = state["messages"][-1].lower()
            if "first" in message and state["flight_search_cache"]:
                state["flight_id"] = state["flight_search_cache"][0]["flightId"]
            elif "second" in message and len(state["flight_search_cache"])>= 1:
                state["flight_id"] = state["flight_search_cache"][1]["flightId"]
            elif "third" in message and len(state["flight_search_cache"]) >= 2:
                state["flight_id"] = state["flight_search_cache"][2]["flightId"]

            if state["sub_action"]=="book":
                state["activity_status"] = "BOOKING"
                state["tool_status"] = "INVOKED"
                missing = []
                if not state["flight_id"]:
                    missing.append("flight ID")
                if not state["passenger_email"]:
                    missing.append("Passenger Email")
                if not state["passenger_name"]:
                    missing.append("Passenger Name")
                if not state["flying_type"]:
                    missing.append("flying type")
                if not state["date_of_birth"]:
                    missing.append("Date of birth")
                if not state["passport_number"]:
                    missing.append("passport number")
                if not state["nationality"]:
                    missing.append("nationality")
                if not state["flight_id"]:
                    missing.append("flight ID")
                if missing:
                    state["activity_status"] = "CLARIFYING"
                    return {
                        "response_text":
                        "I still need:\n" + "\n".join(missing)
                        }
                if not state.get("booking_confirmed"):
                    return {
                        "response_text":
                        (
                            "Please confirm these booking details.\n\n"
                            "Reply with 'Yes' if you'd like me to complete the booking."
                        )
                            }
    
            response = await agent.ainvoke(messages)
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                matching_tool = next(t for t in flight_tools if t.name == tool_call["name"])
                result = _parse_mcp_result(await matching_tool.ainvoke(tool_call["args"]))
                if isinstance(result,list):
                    return{
                        "hotel_results":[],
                        "flight_results":result,
                        "flight_search_cache":result,
                        "response_text":""
                        } 
                if isinstance(result,dict) and result.get("error"):
                    return {"hotel_results":[],"flight_results":[],"response_text":"I couldn't complete that request- the flight service returned an error. Please try again or rephrase your search"}
                return{
                    "hotel_results":[],
                    "flight_results":[],
                    "response_text":str(result),
                    }
            return{
            "response_text":response.content
        }
    except Exception as e:
                traceback.print_exc()
                return {"hotel_results":[],"flight_results":[],"response_text":"Flight search is temporarily unavailable - please try again shortly"}

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

    return {
        "response_text": "I couldn't find matching travel options."
    }


def route_after_extraction(state: GraphState) -> str:
    intent = state.get("intent", "unknown")

    if intent == "hotel":
        return "hotel"

    if intent == "flight":
        return "flight"

    return "unknown"