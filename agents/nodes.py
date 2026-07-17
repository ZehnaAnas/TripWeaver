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
import re
from datetime import datetime
import difflib

VALID_CITIES = [
    'Bali', 'Bangkok', 'Beijing', 'Busan', 'Cebu', 'Delhi', 'Guangzhou', 
    'Hanoi', 'Ho Chi Minh City', 'Jakarta', 'Kuala Lumpur', 'Manila', 
    'Mumbai', 'Osaka', 'Penang', 'Phuket', 'Seoul', 'Shanghai', 
    'Singapore', 'Tokyo'
]

VALID_AIRPORTS = [
    'BKK', 'BOM', 'CAN', 'CGK', 'DEL', 'DPS', 'HAN', 'HKT', 'ICN', 
    'KIX', 'KUL', 'MNL', 'NRT', 'PEK', 'PEN', 'PUS', 'PVG', 'SGN', 'SIN'
]

CITY_TO_AIRPORT = {
    'Bali': 'DPS',
    'Bangkok': 'BKK',
    'Beijing': 'PEK',
    'Busan': 'PUS',
    'Cebu': 'CEB',
    'Delhi': 'DEL',
    'Guangzhou': 'CAN',
    'Hanoi': 'HAN',
    'Ho Chi Minh City': 'SGN',
    'Jakarta': 'CGK',
    'Kuala Lumpur': 'KUL',
    'Manila': 'MNL',
    'Mumbai': 'BOM',
    'Osaka': 'KIX',
    'Penang': 'PEN',
    'Phuket': 'HKT',
    'Seoul': 'ICN',
    'Shanghai': 'PVG',
    'Singapore': 'SIN',
    'Tokyo': 'NRT'
}

COUNTRY_TO_CITIES =  {"indonesia": ["Bali", "Jakarta"],
    "thailand": ["Bangkok", "Phuket"],
    "china": ["Beijing", "Guangzhou", "Shanghai"],
    "south korea": ["Busan", "Seoul"],
    "korea": ["Busan", "Seoul"],
    "philippines": ["Cebu", "Manila"],
    "india": ["Delhi", "Mumbai"],
    "vietnam": ["Hanoi", "Ho Chi Minh City"],
    "malaysia": ["Kuala Lumpur", "Penang"],
    "japan": ["Osaka", "Tokyo"],
    "singapore": ["Singapore"],
}

def validate_and_resolve_city(input_city: str) -> tuple[Optional[str], Optional[str]]:
    """
    Try to figure out which city the user means.
    Returns (resolved_city_name, error_message).
    If resolved_city_name is not None, validation succeeded.
    Otherwise, error_message contains a polite correction/suggestion.
    """
    if not input_city:
        return None, None
        
    cleaned = input_city.strip()
    
    # 1. Exact match (case-insensitive)
    for city in VALID_CITIES:
        if city.lower() == cleaned.lower():
            return city, None
            
    # 2. Exact airport code match
    for city_name, code_val in CITY_TO_AIRPORT.items():
        if code_val.lower() == cleaned.lower():
            return city_name, None
            
    # 3. Partial/similar matches
    similar_matches = []
    for city in VALID_CITIES:
        if cleaned.lower() in city.lower() or city.lower() in cleaned.lower():
            similar_matches.append(city)
            
    if len(similar_matches) == 1:
        return similar_matches[0], None
        
    # Build polite error message
    cities_str = ", ".join(VALID_CITIES)
    if similar_matches:
        similar_str = ", ".join(similar_matches)
        err = (
            f"Sorry!.I couldn't find a supported city matching '{input_city}'. "
            f"Did you mean one of these: {similar_str}?\n\n"
            f"We only support these 20 destinations:\n{cities_str}.\n\n"
            "Please type the exact city name."
        )
    else:
        err = (
            f"Sorry! I couldn't find a supported city matching '{input_city}'. "
            f"We only support the following 20 destinations:\n{cities_str}.\n\n"
            "Please type the exact city name."
        )
    return None, err

def validate_and_resolve_flight_location(input_loc: str) -> tuple[Optional[str], Optional[str]]:
    """
    Try to figure out which city the user means.

    Returns two things:
    - resolved_city: the exact city name if we found a match, otherwise None
    - message: something to say back to the user (a suggestion, a country
      question, or a full list) - only used when resolved_city is None,
      OR when we want to guide them (like the country case)
    """
    if not input_loc:
        return None, None
        
    cleaned = input_loc.strip()
    cleaned_lower = cleaned.lower()
    
    city_list_text = ""
    for city in VALID_CITIES:
        code = CITY_TO_AIRPORT[city]
        city_list_text += f"{city} ({code}),"
    city_list_text = city_list_text.rstrip(",")
   
    if cleaned_lower in COUNTRY_TO_CITIES:
        cities_in_country = COUNTRY_TO_CITIES[cleaned_lower]
        cities_text = "and".join(cities_in_country)
        message = (
            f"Sure! Here are the cities with flights available in {cleaned.title()}:{cities_text}."
            "Which city would you like to visit, and which city are you coming from, also tell me the date you plan to fly if possible so I can check if flights are available for you?"
        )
        return None,message
    
    for city in VALID_CITIES:
        if city.lower() == cleaned_lower:
            return city, None

    for city, code in CITY_TO_AIRPORT.items():
        if code.lower() == cleaned_lower:
            return city, None

    partial_matches = []
    for city in VALID_CITIES:
        if cleaned_lower in city.lower():
            partial_matches.append(city)
    if len(partial_matches) == 1:
        return partial_matches[0], None

    close_matches = difflib.get_close_matches(cleaned, VALID_CITIES, n=3, cutoff=0.6)
    if len(close_matches) == 1:
        return close_matches[0], None
    if len(close_matches) > 1:
        suggestions = ", ".join(close_matches)
        message = (
            f"Sorry, I didn't recognize '{input_loc}' — did you mean {suggestions}?\n\n"
            f"Cities I support: {city_list_text}."
            f"Please choose one from here."
        )
        return None, message

    message = f"Sorry, I couldn't find a place called '{input_loc}'.\n\nCities I support: {city_list_text}. If you find a city you are looking for from here, please let me know"
    return None, message

def validate_date(date_str: str, field_name: str) -> tuple[bool, Optional[str]]:
    """
    Returns (is_valid, error_message).
    """
    if not date_str:
        return True, None
    cleaned = date_str.strip()
    # Match YYYY-MM-DD
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
        return False, (
            f"The format for {field_name} '{date_str}' is invalid. "
            "Please provide the date in YYYY-MM-DD format (for example, 2026-06-15)."
        )
    try:
        datetime.strptime(cleaned, "%Y-%m-%d")
        return True, None
    except ValueError:
        return False, (
            f"The date provided for {field_name} '{date_str}' is not a valid calendar date. "
            "Please check the month/day and enter a valid date in YYYY-MM-DD format."
        )

def validate_email(email_str: str, field_name: str) -> tuple[bool, Optional[str]]:
    if not email_str:
        return True, None
    cleaned = email_str.strip()
    if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
        return False, (
            f"The email address '{email_str}' for {field_name} is invalid. "
            "Please enter a valid email address (for example, guest@example.com)."
        )
    return True, None

def _looks_like_booking_continuation(message: str) -> bool:
    """
    Guess whether this message is continuing an in-progress booking
    (like answering "yes" or giving booking details) versus starting
    something completely new.
    """
    msg = message.strip().lower()

    if msg == "":
        return False

    # Common confirmation words
    confirmation_words = ["yes", "no", "confirm", "cancel", "proceed"]
    if msg in confirmation_words:
        return True

    # Ordinal words like "book the first one"
    ordinal_words = ["first", "second", "third", "fourth", "fifth", "last",
                      "1st", "2nd", "3rd", "4th", "5th"]
    for word in ordinal_words:
        if word in msg:
            return True

    # An email address is a strong sign they're filling in booking details
    if "@" in msg:
        return True

    # A message with several commas is probably a details dump like:
    # "Zehna, zehna@email.com, 2026-04-03, 2026-04-06, single"
    if msg.count(",") >= 2:
        return True

    # A date in YYYY-MM-DD format
    date_pattern = re.search(r"\d{4}-\d{1,2}-\d{1,2}", msg)
    if date_pattern:
        return True


    return False
def resolve_hotel_name_from_cache_or_search(hotel_name_query: str, cache: list[dict], available_hotels: list[dict] = None) -> tuple[Optional[str], Optional[str]]:
    """
    Returns (resolved_exact_name, error_message).
    """
    if not hotel_name_query:
        return None, None
    
    query = hotel_name_query.strip().lower()
    
    # Check cache first
    candidates = []
    for h in cache:
        h_name = h.get("hotelName") or h.get("name")
        if h_name:
            if query == h_name.lower():
                return h_name, None
            if query in h_name.lower() or h_name.lower() in query:
                candidates.append(h_name)
                
    if len(candidates) == 1:
        return candidates[0], None
    elif len(candidates) > 1:
        candidates_str = "\n".join([f"- {c}" for c in candidates])
        return None, (
            f"I found multiple hotels matching '{hotel_name_query}' in your search results:\n"
            f"{candidates_str}\n\n"
            "Please type the exact hotel name you would like to book."
        )
        
    # If not in cache, check available_hotels
    if available_hotels:
        candidates = []
        for h in available_hotels:
            h_name = h.get("hotelName") or h.get("name")
            if h_name:
                if query == h_name.lower():
                    return h_name, None
                if query in h_name.lower() or h_name.lower() in query:
                    candidates.append(h_name)
        if len(candidates) == 1:
            return candidates[0], None
        elif len(candidates) > 1:
            candidates_str = "\n".join([f"- {c}" for c in candidates])
            return None, (
                f"I found multiple hotels matching '{hotel_name_query}':\n"
                f"{candidates_str}\n\n"
                "Please type the exact hotel name you would like to book."
            )
            
    return None, (
        f"I couldn't find a hotel named '{hotel_name_query}'. "
        "Please check the spelling or enter a hotel name from your search results."
    )


def resolve_flight_id_from_airline(airline_query: str, cache: list[dict], all_flights: list[dict] = None) -> tuple[Optional[str], Optional[str]]:
    """
    Returns (resolved_flight_id, error_message).
    """
    if not airline_query:
        return None, None

    query = airline_query.strip().lower()

    # Try to find match in cache first
    candidates = []
    for f in cache:
        f_airline = f.get("airline")
        f_id = f.get("flightId") or f.get("_id")
        if f_airline and f_id:
            if query in f_airline.lower() or f_airline.lower() in query:
                candidates.append(f)

    if len(candidates) == 1:
        return candidates[0]["flightId"], None
    elif len(candidates) > 1:
        lines = []
        for c in candidates:
            lines.append(
                f"- Flight {c.get('flightNumber', 'N/A')} by {c.get('airline')} "
                f"on {c.get('flightDate', 'N/A')} "
                f"({c.get('departureTime', 'N/A')} - {c.get('arrivalTime', 'N/A')}, Price: {c.get('price')})"
            )
        options_str = "\n".join(lines)
        return None, (
            f"I found multiple flight options for '{airline_query}' in your search results:\n"
            f"{options_str}\n\n"
            "Please specify more details or type the exact flight details."
        )

    # If not in cache, check all_flights if provided
    if all_flights:
        candidates = []
        for f in all_flights:
            f_airline = f.get("airline")
            f_id = f.get("flightId") or f.get("_id")
            if f_airline and f_id:
                if query in f_airline.lower() or f_airline.lower() in query:
                    candidates.append(f)
        if len(candidates) == 1:
            return candidates[0]["flightId"], None
        elif len(candidates) > 1:
            lines = []
            for c in candidates:
                lines.append(
                    f"- Flight {c.get('flightNumber', 'N/A')} by {c.get('airline')} "
                    f"on {c.get('flightDate', 'N/A')} "
                    f"from {c.get('originCity') or c.get('originAirport')} to {c.get('destinationCity') or c.get('destinationAirport')} "
                    f"({c.get('departureTime')} - {c.get('arrivalTime')}, Price: {c.get('price')})"
                )
            options_str = "\n".join(lines)
            return None, (
                f"I found multiple flight options for '{airline_query}':\n"
                f"{options_str}\n\n"
                "Please specify your flight or type the exact flight details."
            )

    return None, (
        f"I couldn't find any flights operated by '{airline_query}'. "
        "Please verify the airline name or search for flights first."
    )
def _is_decline(message: str) -> bool:
    """
    Detects an explicit "no, don't book this" from the user - the FIRST
    signal that something's wrong, before we know whether they want to
    cancel entirely or just fix a detail.
    """
    msg = message.strip().lower()
    return msg in ["no", "cancel", "decline", "nevermind", "never mind", "stop",
                   "don't book it", "dont book it", "nope", "nah"]


def _is_cancel_confirmation(message: str) -> bool:
    """
    Detects a clear "yes, actually cancel it" - used ONLY as the second
    step, after we've already asked "cancel, or just fix something?".
    This is deliberately narrow (a real yes/cancel word) so that if the
    user instead starts giving corrected details, we don't misread that
    as a cancellation.
    """
    msg = message.strip().lower()
    return msg in ["yes", "cancel", "cancel it", "yes cancel", "yes cancel it", "confirm cancel"]
class TravelExtraction(BaseModel):
    intent: Literal["hotel", "flight","weather","activities","itinerary","unknown"] = Field(
        default="unknown",
        description= "Main user intent: hotel, flight, weather (forecast for a city), "
            "activities (things to do/attractions in a city), itinerary (combine a previously "
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
    description="Hotel name which the user specifies. Null if not provided"
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

    booking_confirmed_this_turn = user_message.strip().lower() in ["yes","confirm","proceed"]
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
    if resolved_intent == "unknown" and state.get("last_intent") in ("hotel","flight","weather","activities"):
        resolved_intent = state["last_intent"]
        
    was_booking = state.get("sub_action") == "book"
    extractor_found_new_intent = data.get("intent") not in (None, "unknown")
    continuing_booking = _looks_like_booking_continuation(user_message)

    give_up_on_booking = was_booking and not extractor_found_new_intent and not continuing_booking

    if give_up_on_booking:
        resolved_intent = "unknown"

    if give_up_on_booking:
        final_sub_action = "general"
        final_booking_confirmed = False
    else:
        if data.get("sub_action") in (None, "general") and state.get("sub_action") == "book":
            final_sub_action = "book"
        else:
            final_sub_action = data.get("sub_action") or state.get("sub_action", "general")
        final_booking_confirmed = booking_confirmed_this_turn or state.get("booking_confirmed", False)

    return {

    "intent": resolved_intent,
    "sub_action":  final_sub_action,
    "last_intent":resolved_intent if resolved_intent in ("hotel","flight","weather","activities") else state.get("last_intent"),

    "city": data.get("city") or state.get("city"),
    "city_code": data.get("city_code") or state.get("city_code"),

    "check_in": data.get("check_in") or state.get("check_in"),
    "check_out": data.get("check_out") or state.get("check_out"),

    "origin": data.get("origin") or state.get("origin"),
    "destination": data.get("destination") or state.get("destination"),

    "flight_date": data.get("flight_date") or state.get("flight_date"),

    "hotel_id": state.get("hotel_id"),
    "flight_id": state.get("flight_id"),
    "booking_confirmed": final_booking_confirmed,

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
    "activity_type": data.get("activity_type"),
   
    "activity_status":"ROUTING",
    "tool_status": state.get("tool_status"),

    "hotel_results": [],
    "flight_results": [],
    "weather_results": [],
    "activity_results": [],
    "hotel_search_cache": state.get("hotel_search_cache", []),
    "flight_search_cache": state.get("flight_search_cache", []),

    "response_text": ""
}
    

def _format_hotel(hotel: dict) -> str:
    name = hotel.get("hotelName", "Unknown hotel")

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


async def hotel_node(state: GraphState) -> dict:
    try:
        message = state["messages"][-1].lower()
        cache = state.get("hotel_search_cache", [])
        resolved_hotel_name = state.get("hotel_name")
        if not resolved_hotel_name or state.get("sub_action") == "book":
            if "first" in message and len(cache) >= 1:
                resolved_hotel_name = cache[0].get("hotelName") or cache[0].get("name")
            elif "second" in message and len(cache) >= 2:
                resolved_hotel_name = cache[1].get("hotelName") or cache[1].get("name")
            elif "third" in message and len(cache) >= 3:
                resolved_hotel_name = cache[2].get("hotelName") or cache[2].get("name")
            else:
                for h in cache:
                    h_name = h.get("hotelName") or h.get("name")
                    if h_name and h_name.lower() in message:
                        resolved_hotel_name = h_name
                        break

        if state.get("sub_action") == "book" and resolved_hotel_name:
            already_verified = any(
                (h.get("hotelName") or h.get("name") or "").lower() == resolved_hotel_name.lower()
                for h in cache
            )

            if not already_verified:
                matches = []
                try:
                    async with mcp_client.session("hotel") as session:
                        hotel_tools = await load_mcp_tools(session)
                        search_tool = next((t for t in hotel_tools if t.name == "search_hotel"), None)
                        if search_tool is not None:
                            search_args = {"hotel_name": resolved_hotel_name}
                            if state.get("city"):
                                search_args["city"] = state["city"]
                            raw = await search_tool.ainvoke(search_args)
                            parsed = _parse_mcp_result(raw)
                            if isinstance(parsed, list):
                                matches = parsed
                except Exception:
                    matches = []

                if len(matches) == 0:
                    city_text = f" in {state['city']}" if state.get("city") else ""
                    return {
                        "activity_status": "CLARIFYING",
                        "response_text": (
                            f"I couldn't find a hotel called \"{resolved_hotel_name}\"{city_text}. "
                            "Could you double-check the name, or would you like me to list hotels there instead?"
                        ),
                    }

                if len(matches) == 1:
                    resolved_hotel_name = matches[0].get("hotelName") or matches[0].get("name")
                    cache = matches

                if len(matches) > 1:
                    option_lines = []
                    for h in matches:
                        name = h.get("hotelName") or h.get("name")
                        stars = h.get("starRating", "N/A")
                        price = h.get("pricePerNight", "N/A")
                        rooms = h.get("availableRooms", "N/A")
                        option_lines.append(f"- {name}: {stars} stars, USD {price}/night, {rooms} rooms available")
                    return {
                        "hotel_search_cache": matches,
                        "activity_status": "CLARIFYING",
                        "response_text": (
                            f"I found a few hotels called \"{resolved_hotel_name}\":\n"
                            + "\n".join(option_lines)
                            + "\n\nWhich one would you like to book? You can name it exactly, or say \"the first one\", \"the second one\", etc."
                        ),
                    }

        check_in = state.get("check_in")
        if check_in:
            ok, err = validate_date(check_in, "check-in date")
            if not ok:
                err = err or "The check-in date is invalid."
                return {"activity_status": "CLARIFYING", "response_text": f"{err} For example: 2026-06-15."}

        check_out = state.get("check_out")
        if check_out:
            ok, err = validate_date(check_out, "check-out date")
            if not ok:
                err = err or "The check-out date is invalid."
                return {"activity_status": "CLARIFYING", "response_text": f"{err} For example: 2026-06-20."}

        if check_in and check_out:
            try:
                if datetime.strptime(check_out, "%Y-%m-%d") <= datetime.strptime(check_in, "%Y-%m-%d"):
                    return {"activity_status": "CLARIFYING", "response_text": f"Check-out ({check_out}) must be after check-in ({check_in}). Please correct the dates."}
            except ValueError:
                pass

        guest_email = state.get("guest_email")
        if guest_email:
            ok, err = validate_email(guest_email, "guest email")
            if not ok:
                err = err or "The guest email address is invalid."
                return {"activity_status": "CLARIFYING", "response_text": f"{err} For example: jane@example.com."}

        room_type = state.get("room_type")
        VALID_ROOM_TYPES = ["single", "double", "suite", "deluxe"]
        if room_type and room_type.lower() not in VALID_ROOM_TYPES:
            return {
                "activity_status": "CLARIFYING",
                "response_text": f"'{room_type}' isn't a room type I recognise. Please choose one of: {', '.join(VALID_ROOM_TYPES)}.",
            }

        if state.get("sub_action") == "book":
            if state.get("awaiting_cancel_decision"):
                if _is_cancel_confirmation(state["messages"][-1]):
                    return {
                        "hotel_name": None,
                        "guest_name": None,
                        "guest_email": None,
                        "check_in": None,
                        "check_out": None,
                        "room_type": None,
                        "sub_action": "general",
                        "last_intent": None,
                        "booking_confirmed": False,
                        "awaiting_cancel_decision": False,
                        "hotel_results": [], "flight_results": [],
                        "response_text": "Booking cancelled! Let me know if you have any other questions or need anything else.",
                    }
                return {
                    "awaiting_cancel_decision": False,
                    "activity_status": "CLARIFYING",
                    "response_text": "Got it! Please tell me the correct details and I'll update your booking.",
                }
            if not resolved_hotel_name:
                if not cache:
                    known_city = state.get("city")
                    known_city_code = state.get("city_code")
                    if not known_city and not known_city_code:
                        for candidate_city in VALID_CITIES:
                            if candidate_city.lower() in message:
                                known_city = candidate_city
                                break
 
                    if not known_city and not known_city_code:
                        return {
                        "activity_status": "CLARIFYING",
                        "response_text": (
                            "Happy to help you book a hotel! First, let's find one - "
                            "which city would you like to stay in? "
                            "(You can also tell me your check-in/check-out dates, budget, "
                            "or star rating now if you'd like - those are optional and just narrow the results.)"
                        ),
                    }
                    resolved_city = known_city
                    if known_city:
                        resolved_city, err = validate_and_resolve_city(known_city)
                        if err:
                            return {"activity_status": "CLARIFYING", "response_text": err}
 
                    search_results = []
                    try:
                        async with mcp_client.session("hotel") as session:
                            hotel_tools = await load_mcp_tools(session)
                            search_tool = next((t for t in hotel_tools if t.name == "search_hotel"), None)
                            if search_tool is not None:
                                search_args = {}
                                if resolved_city:
                                    search_args["city"] = resolved_city
                                if known_city_code:
                                    search_args["city_code"] = known_city_code
                                if state.get("check_in"):
                                    search_args["check_in"] = state["check_in"]
                                if state.get("check_out"):
                                    search_args["check_out"] = state["check_out"]
                                if state.get("hotel_budget"):
                                    search_args["hotel_budget"] = state["hotel_budget"]
                                if state.get("star_rating"):
                                    search_args["star_rating"] = state["star_rating"]
 
                                raw = await search_tool.ainvoke(search_args)
                                parsed = _parse_mcp_result(raw)
 
                                error_message = _extract_mcp_error(parsed)
                                if error_message:
                                    return {
                                        "city": resolved_city,
                                        "activity_status": "CLARIFYING",
                                        "response_text": f"I couldn't complete that search — {error_message}",
                                    }
 
                                if isinstance(parsed, list):
                                    search_results = parsed
                    except Exception:
                        search_results = []
 
                    if not search_results:
                        city_text = resolved_city or known_city_code or "that city"
                        return {
                            "city": resolved_city,
                            "activity_status": "CLARIFYING",
                            "response_text": f"I couldn't find any hotels in \"{city_text}\". Try a nearby major city, e.g. Bangkok, Seoul, Tokyo, Singapore.",
                        }
 
                    lines = [_format_hotel(h) for h in search_results[:5]]
                    count = len(search_results)
                    return {
                        "city": resolved_city,
                        "hotel_search_cache": search_results,
                        "hotel_results": search_results,
                        "activity_status": "CLARIFYING",
                        "response_text": (
                            f"I found {count} hotel option{'s' if count != 1 else ''}:\n"
                            + "\n".join(lines)
                            + "\n\nWhich one would you like to book? You can name it exactly, or say \"the first one\", \"the second one\", etc."
                        ),
                    }
                return {"activity_status": "CLARIFYING", "response_text": "Which hotel would you like to book? Please give the exact hotel name (e.g. \"Shangri-La PUS 1\") or say \"the first one\"/\"the second one\"."}
            missing = []
            if not state.get("guest_name"):
                missing.append("guest name (e.g. \"Jane Doe\")")
            if not state.get("guest_email"):
                missing.append("guest email (e.g. \"jane@example.com\")")
            if not check_in:
                missing.append("check-in date (e.g. \"2026-06-15\")")
            if not check_out:
                missing.append("check-out date (e.g. \"2026-06-20\")")
            if not room_type:
                missing.append(f"room type ({', '.join(VALID_ROOM_TYPES)})")

            if missing:
                if len(missing) == 1:
                    missing_text = missing[0]
                else:
                    missing_text = ", ".join(missing[:-1]) + f", and {missing[-1]}"

                return {
                    "hotel_name": resolved_hotel_name,
                    "activity_status": "CLARIFYING",
                    "response_text": f"Great choice — {resolved_hotel_name}! To book it, could you share your {missing_text}?",
                }

            if not state.get("booking_confirmed"):
                if _is_decline(state["messages"][-1]):
                    return {
                        "awaiting_cancel_decision": True,
                        "activity_status": "CLARIFYING",
                        "response_text": (
                            "No problem! Would you like to cancel this booking, or just fix a detail? "
                            "If something's wrong, just tell me the correct information and I'll update it."
                        ),
                    }
                return {
                    "hotel_name": resolved_hotel_name,
                    "activity_status": "CLARIFYING",
                    "response_text": (
                        f"Please confirm these booking details:\n"
                        f"- Hotel: {resolved_hotel_name}\n"
                        f"- Guest: {state['guest_name']}\n"
                        f"- Email: {state['guest_email']}\n"
                        f"- Check-in: {check_in}\n"
                        f"- Check-out: {check_out}\n"
                        f"- Room type: {room_type}\n\n"
                        "Reply 'Yes' to confirm."
                    ),
                }

        async with mcp_client.session("hotel") as session:
            hotel_tools = await load_mcp_tools(session)
            agent = llm.bind_tools(hotel_tools)
            messages = [
                SystemMessage(content=(
                    "You are the hotel booking agent. Use search_hotel/list_all_hotels/book_hotel as appropriate. "
                    "Always call the search tool fresh for availability questions - never answer from memory. "
                    "Never invent a hotel name - it must come from a real search result."
                )),
                *[HumanMessage(content=m) for m in state["messages"]],
            ]
            response = await agent.ainvoke(messages)

            if response.tool_calls:
                tool_call = response.tool_calls[0]
                matching_tool = next(t for t in hotel_tools if t.name == tool_call["name"])
                args = dict(tool_call["args"])
                if tool_call["name"] == "book_hotel":
                    args = {
                        "hotel_name": resolved_hotel_name,
                        "check_in": state["check_in"],
                        "check_out": state["check_out"],
                        "guest_name": state["guest_name"],
                        "guest_email": state["guest_email"],
                        "room_type": state["room_type"],
                    }

                result = _parse_mcp_result(await matching_tool.ainvoke(args))
                error_message = _extract_mcp_error(result)

                if error_message:
                    return {"hotel_name": resolved_hotel_name, "hotel_results": [], "flight_results": [],
                            "response_text": f"I couldn't complete that request — {error_message}"}

                confirmation = result[0] if isinstance(result, list) and len(result) == 1 else result
                if isinstance(confirmation, dict) and confirmation.get("confirmationId"):
                    city_for_followup = state.get("city") or "that area"
                    price_line = ""
                    matching_hotel = None
                    for h in cache:
                        name = h.get("hotelName") or h.get("name")
                        if name and name.lower() == resolved_hotel_name.lower():
                            matching_hotel = h
                            break
 
                    if matching_hotel and matching_hotel.get("pricePerNight") is not None:
                        try:
                            nights = (
                                datetime.strptime(confirmation["checkOutDate"], "%Y-%m-%d")
                                - datetime.strptime(confirmation["checkInDate"], "%Y-%m-%d")
                            ).days
                            if nights > 0:
                                price_per_night = matching_hotel["pricePerNight"]
                                total_price = nights * price_per_night
                                price_line = (
                                    f"Price: USD {price_per_night}/night x {nights} night{'s' if nights != 1 else ''} "
                                    f"= USD {total_price} total\n"
                                )
                        except ValueError:
                            pass
 
                    return {
                        "hotel_name": resolved_hotel_name,
                        "booking_confirmed": False,
                        "hotel_results": [], "flight_results": [],
                        "response_text": (
                            f"🎉 You're booked!\n\n"
                            f"Confirmation ID: {confirmation['confirmationId']}\n"
                            f"Hotel: {confirmation['hotelName']}\n"
                            f"Guest: {confirmation['guestName']} ({confirmation['guestEmail']})\n"
                            f"Check-in: {confirmation['checkInDate']} → Check-out: {confirmation['checkOutDate']}\n"
                            f"Room: {confirmation['roomType']}\n"
                            f"{price_line}\n"
                            f"Would you like to book a flight? Find places you would like to visit in {city_for_followup}? Or check the weather there?"
                        ),
                        "traveling_to_city": state.get("city") or state.get("traveling_to_city"),
                    }
                if isinstance(result, list):
                    if len(result) == 0 and (args.get("city")):
                        return {"hotel_results": [], "flight_results": [],
                                "response_text": f"I couldn't find any hotels in \"{args['city']}\". Try a nearby major city, e.g. Bangkok, Seoul, Tokyo, Singapore."}
                    return {"hotel_name": resolved_hotel_name, "hotel_results": result,
                            "hotel_search_cache": result, "flight_results": [], "response_text": ""}

                return {"hotel_name": resolved_hotel_name, "hotel_results": [], "flight_results": [], "response_text": str(result)}

            return {"hotel_name": resolved_hotel_name, "response_text": response.content}
    except Exception:
        traceback.print_exc()
        return {"hotel_results": [], "flight_results": [], "response_text": "The hotel booking service is currently unavailable. Please try again shortly."}
    
async def flight_node(state: GraphState) -> dict:
    try:
        message = state["messages"][-1].lower()
        resolved_flight_id = state.get("flight_id")
        cache = state.get("flight_search_cache", [])

        flight_date = state.get("flight_date")
        if flight_date:
            is_ok, err = validate_date(flight_date, "flight date")
            if not is_ok:
                return {"activity_status": "CLARIFYING", "response_text": err}

        flight_budget = state.get("flight_budget")
        if flight_budget is not None:
            try:
                budget_val = int(flight_budget)
                if budget_val <= 0:
                    return {
                        "activity_status": "CLARIFYING",
                        "response_text": "The flight budget must be a positive number. Please enter a valid budget."
                    }
            except ValueError:
                return {
                    "activity_status": "CLARIFYING",
                    "response_text": "The flight budget is invalid. Please enter a valid number."
                }

        passenger_email = state.get("passenger_email")
        if passenger_email:
            is_ok, err = validate_email(passenger_email, "passenger email")
            if not is_ok:
                return {"activity_status": "CLARIFYING", "response_text": err}

        dob = state.get("date_of_birth")
        if dob:
            is_ok, err = validate_date(dob.replace("/", "-"), "date of birth")
            if not is_ok:
                return {"activity_status": "CLARIFYING", "response_text": err}

        adjusted_flight_budget = state.get("flight_budget")
        if state.get("budget_adjustment") == "lower" and adjusted_flight_budget:
            adjusted_flight_budget = max(1, int(adjusted_flight_budget * 0.7))
        elif state.get("budget_adjustment") == "higher" and adjusted_flight_budget:
            adjusted_flight_budget = int(adjusted_flight_budget * 1.3)

        resolved_flight_id = state.get("flight_id")
        if "first" in message and len(cache) >= 1:
            resolved_flight_id = cache[0].get("flightId")
        elif "second" in message and len(cache) >= 2:
            resolved_flight_id = cache[1].get("flightId")
        elif "third" in message and len(cache) >= 3:
            resolved_flight_id = cache[2].get("flightId")

        airline = state.get("airline")
        if state.get("sub_action") == "book":
            if state.get("awaiting_cancel_decision"):
                if _is_cancel_confirmation(state["messages"][-1]):
                    return {
                        "flight_id": None,
                        "airline": None,
                        "passenger_name": None,
                        "passenger_email": None,
                        "flying_type": None,
                        "date_of_birth": None,
                        "passport_number": None,
                        "nationality": None,
                        "sub_action": "general",
                        "last_intent": None,
                        "booking_confirmed": False,
                        "awaiting_cancel_decision": False,
                        "hotel_results": [], "flight_results": [],
                        "response_text": "Booking cancelled! Let me know if you have any other questions or need anything else.",
                    }
                state["awaiting_cancel_decision"] = False
            if not resolved_flight_id and not airline and not cache:
                return {
                    "activity_status": "CLARIFYING",
                    "response_text": (
                        "Happy to help you book a flight! First, let's find one - "
                        "which city are you flying from, and which city are you flying to? "
                        "(You can also tell me a date, budget, or preferred departure time now "
                        "if you'd like - those are optional and just narrow the results.)"
                    ),
                }

            if not resolved_flight_id and airline:
                resolved_id, err = resolve_flight_id_from_airline(airline, cache)
                if err:
                    try:
                        async with mcp_client.session("flight") as session:
                            flight_tools = await load_mcp_tools(session)
                            list_tool = next(t for t in flight_tools if t.name == "get_all_flights")
                            all_flights = _parse_mcp_result(await list_tool.ainvoke({}))
                            resolved_id, err2 = resolve_flight_id_from_airline(airline, cache, all_flights)
                            if err2:
                                return {"activity_status": "CLARIFYING", "response_text": err2}
                    except Exception:
                        pass
                if resolved_id:
                    resolved_flight_id = resolved_id

            if not resolved_flight_id and not airline and cache:
                return {
                    "activity_status": "CLARIFYING",
                    "response_text": "Which flight would you like to book? You can name the airline (e.g. \"the Japan Airlines one\") or say its position (e.g. \"the first one\").",
                }

            missing = []
            if not resolved_flight_id and not airline:
                missing.append("the airline or flight you'd like (e.g. \"the Japan Airlines flight\" or name the exact flight number)")
            if not state.get("passenger_email"):
                missing.append("passenger email (e.g. \"jane@example.com\")")
            if not state.get("passenger_name"):
                missing.append("passenger name (e.g. \"Jane Doe\")")
            if not state.get("flying_type"):
                missing.append("flying type (economy, business, or first class)")
            if not state.get("date_of_birth"):
                missing.append("date of birth (e.g. \"1995-08-20\")")
            if not state.get("passport_number"):
                missing.append("passport number (e.g. \"N1234567\")")
            if not state.get("nationality"):
                missing.append("nationality (e.g. \"Sri Lankan\")")

            if missing:
                if len(missing) == 1:
                    missing_text = missing[0]
                else:
                    missing_text = ", ".join(missing[:-1]) + f", and {missing[-1]}"
                return {
                    "flight_id": resolved_flight_id,
                    "activity_status": "CLARIFYING",
                    "response_text": f"Great choice — {airline}! To book it, could you share your {missing_text}?",
                }

            if not state.get("booking_confirmed"):
                if _is_decline(state["messages"][-1]):
                    return {
                        "awaiting_cancel_decision": True,
                        "activity_status": "CLARIFYING",
                        "response_text": (
                            "No problem! Would you like to cancel this booking, or just fix a detail? "
                            "If something's wrong, just tell me the correct information and I'll update it."
                        ),
                    }
                details = (
                    f"- Airline: {airline or 'Resolved'}\n"
                    f"- Flight ID: {resolved_flight_id}\n"
                    f"- Passenger Name: {state.get('passenger_name')}\n"
                    f"- Passenger Email: {state.get('passenger_email')}\n"
                    f"- Flying Type: {state.get('flying_type')}\n"
                    f"- Date of Birth: {state.get('date_of_birth')}\n"
                    f"- Passport Number: {state.get('passport_number')}\n"
                    f"- Nationality: {state.get('nationality')}\n"
                )
                return {
                    "flight_id": resolved_flight_id,
                    "activity_status": "CLARIFYING",
                    "response_text": f"Please confirm these booking details:\n{details}\nReply with 'Yes' if you'd like me to complete the booking.",
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
                    "updates the system's flight cache that later booking steps depend on. "
                    "The search_flights tool accepts city names, airport codes, OR country names for both "
                    "origin and destination - just pass through whatever the user said, don't try to convert "
                    "it yourself. If the tool returns an error, relay its message honestly instead of inventing "
                    "airlines, prices, or IDs. "
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
                if tool_call["name"] == "book_flight":
                    resolved_airline = airline or next(
                        (f.get("airline") for f in cache if f.get("flightId") == resolved_flight_id), None
                    )
                    args = {
                        "airline": resolved_airline,
                        "passenger_name": state.get("passenger_name"),
                        "passenger_email": state.get("passenger_email"),
                        "flying_type": state.get("flying_type"),
                        "date_of_birth": state.get("date_of_birth"),
                        "passport_number": state.get("passport_number"),
                        "nationality": state.get("nationality"),
                    }
                if tool_call["name"] == "search_flights" and adjusted_flight_budget:
                    args["flight_budget"] = adjusted_flight_budget

                result = _parse_mcp_result(await matching_tool.ainvoke(args))
                error_message = _extract_mcp_error(result)

                if error_message:
                    return {
                        "flight_id": resolved_flight_id,
                        "hotel_results": [], "flight_results": [],
                        "response_text": f"I couldn't complete that request — {error_message}",
                    }

                confirmation = result[0] if isinstance(result, list) and len(result) == 1 else result
                if isinstance(confirmation, dict) and confirmation.get("confirmationId"):
                    matched_flight = None
                    if resolved_flight_id:
                        for f in cache:
                            if f.get("flightId") == resolved_flight_id:
                                matched_flight = f
                                break
                    if matched_flight is None and confirmation.get("airline"):
                        for f in cache:
                            if (f.get("airline") or "").lower() == confirmation["airline"].lower():
                                matched_flight = f
                                break
 
                    price_line = ""
                    flight_details_line = ""
                    if matched_flight:
                        if matched_flight.get("price") is not None:
                            price_line = f"Price: USD {matched_flight['price']}\n"
                        flight_date = matched_flight.get("flightDate", "N/A")
                        departure_time = matched_flight.get("departureTime", "N/A")
                        arrival_time = matched_flight.get("arrivalTime", "N/A")
                        flight_details_line = f"Flight date: {flight_date} ({departure_time} → {arrival_time})\n"
 
                    return {
                        "flight_id": resolved_flight_id,
                        "booking_confirmed": False,
                        "hotel_results": [], "flight_results": [],
                        "response_text": (
                            f"🎉 You're booked!\n\n"
                            f"Confirmation ID: {confirmation['confirmationId']}\n"
                            f"Airline: {confirmation['airline']}\n"
                            f"{flight_details_line}"
                            f"Passenger: {confirmation['passengerName']} ({confirmation['passengerEmail']})\n"
                            f"Class: {confirmation['flyingType']}\n"
                            f"Passport: {confirmation['passportNumber']} ({confirmation['nationality']})\n"
                            f"{price_line}\n"
                            f"Would you like to book a flight? Find places to visit? Or check the weather there?"
                        ),
                        "traveling_to_city": (matched_flight.get("destinationCity") if matched_flight else None) or state.get("traveling_to_city"),
                    }
                if isinstance(confirmation, dict) and "flights" in confirmation:
                    flight_list = confirmation["flights"]
                    note = confirmation.get("note", "")
                    formatted_lines = [_format_flight(f) for f in flight_list[:5]]
                    count = len(flight_list)
                    response_text = (
                        f"I found {count} flight option{'s' if count != 1 else ''}:\n"
                        + "\n".join(formatted_lines)
                    )
                    if note:
                        response_text += f"\n\n{note}"
                    return {
                        "flight_id": resolved_flight_id,
                        "flight_budget": adjusted_flight_budget,
                        "budget_adjustment": None,
                        "hotel_results": [],
                        "flight_results": flight_list,
                        "flight_search_cache": flight_list,
                        "response_text": response_text,
                    }

                if isinstance(result, list):
                    return {
                        "flight_id": resolved_flight_id,
                        "flight_budget": adjusted_flight_budget,
                        "budget_adjustment": None,
                        "hotel_results": [],
                        "flight_results": result,
                        "flight_search_cache": result,
                        "response_text": "",
                    }

                return {
                    "flight_id": resolved_flight_id,
                    "booking_confirmed": False,
                    "hotel_results": [], "flight_results": [],
                    "response_text": str(result),
                }

            return {"flight_id": resolved_flight_id, "response_text": response.content}

    except Exception:
        traceback.print_exc()
        return {
            "hotel_results": [], "flight_results": [],
            "response_text": "Flight search is temporarily unavailable — please try again shortly.",
        }
async def weather_node(state: GraphState) -> dict:
    try:
        city = state.get("city")
        if city:
            resolved_city, err = validate_and_resolve_city(city)
            if err:
                return {
                    "activity_status": "CLARIFYING",
                    "response_text": err
                }
            state["city"] = resolved_city

        weather_date = state.get("weather_date")
        if weather_date:
            is_ok, err = validate_date(weather_date, "weather forecast date")
            if not is_ok:
                return {"activity_status": "CLARIFYING", "response_text": err}

        async with mcp_client.session("weather") as session:
            weather_tools = await load_mcp_tools(session)
            agent = llm.bind_tools(weather_tools)

            messages = [
                SystemMessage(content=(
                    "You are the weather agent. Use the available tool to get a forecast for the city the user is asking about. "
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

                weather_data = result[0] if isinstance(result, list) and len(result) == 1 else result

                error_message = _extract_mcp_error(weather_data)
                if error_message:
                    return {
                        "weather_results": [],
                        "response_text": f"I couldn't get the weather for that city - {error_message}"
                    }

                return {
                    "weather_results": [weather_data] if isinstance(weather_data, dict) else (weather_data if isinstance(weather_data, list) else []),
                    "response_text": "",
                }

            return {"response_text": response.content}
    except Exception:
        traceback.print_exc()
        return {
            "weather_results": [],
            "response_text": "The weather service is currently unavailable. Please try again shortly."
        }
    
async def places_node(state: GraphState) -> dict:
    try:
        message = state["messages"][-1].lower()
        cache = state.get("activity_search_cache", [])
        planned = state.get("planned_activities", [])

        # --- Handle "add X to my plan" ---
        if ("add" in message and "plan" in message) or "add it" in message:
            matched_place = None
            for place in cache:
                name = place.get("name", "")
                if name and name.lower() in message:
                    matched_place = place
                    break
            if not matched_place:
                if "first" in message and len(cache) >= 1:
                    matched_place = cache[0]
                elif "second" in message and len(cache) >= 2:
                    matched_place = cache[1]
                elif "third" in message and len(cache) >= 3:
                    matched_place = cache[2]

            if matched_place:
                already_planned = any(
                    p.get("name") == matched_place.get("name") for p in planned
                )
                if not already_planned:
                    planned = planned + [matched_place]
                return {
                    "planned_activities": planned,
                    "activity_results": [],
                    "response_text": (
                        f"Added \"{matched_place.get('name')}\" to your plan! "
                        f"You've got {len(planned)} thing{'s' if len(planned) != 1 else ''} planned so far. "
                        "Want to add anything else, or hear more about one of them?"
                    ),
                }
            if not cache:
                return {
                    "activity_results": [],
                    "response_text": "Let's find some places to visit first! Search for places in a city, then tell me which one to add.",
                }
            return {
                "activity_results": [],
                "response_text": "Which place would you like to add? You can name it exactly, or say \"the first one\", etc.",
            }

        wants_to_see_plan = any(
            phrase in message for phrase in ["what's on my plan", "whats on my plan", "show my plan", "my plan so far"]
        )
        if wants_to_see_plan:
            if not planned:
                return {
                    "activity_results": [],
                    "response_text": "You haven't added anything to your plan yet! Search for places to visit, then say \"add [name] to my plan\".",
                }
            lines = [f"- {p.get('name')}" for p in planned]
            return {
                "activity_results": [],
                "response_text": "Here's your plan so far:\n" + "\n".join(lines),
            }

        wants_more_info = any(phrase in message for phrase in ["more info", "tell me more", "more about"])
        if wants_more_info:
            matched_place = None
            for place in cache:
                name = place.get("name", "")
                if name and name.lower() in message:
                    matched_place = place
                    break
            if not matched_place and cache:
                if "first" in message and len(cache) >= 1:
                    matched_place = cache[0]
                elif "second" in message and len(cache) >= 2:
                    matched_place = cache[1]
                elif "third" in message and len(cache) >= 3:
                    matched_place = cache[2]

            place_name_for_lookup = matched_place.get("name") if matched_place else None
            city_for_lookup = state.get("city") or state.get("traveling_to_city")

            if not place_name_for_lookup:
                return {
                    "activity_results": [],
                    "response_text": "Which place would you like more info on? Please name it exactly from the list I showed you.",
                }

            try:
                async with mcp_client.session("places") as session:
                    place_tools = await load_mcp_tools(session)
                    details_tool = next((t for t in place_tools if t.name == "get_place_details"), None)
                    if details_tool is not None:
                        raw = await details_tool.ainvoke({
                            "place_name": place_name_for_lookup,
                            "city": city_for_lookup or "",
                        })
                        parsed = _parse_mcp_result(raw)
                        info = parsed[0] if isinstance(parsed, list) and len(parsed) == 1 else parsed
                        error_message = _extract_mcp_error(info)
                        if error_message:
                            return {
                                "activity_results": [],
                                "response_text": f"I couldn't find more info about {place_name_for_lookup} - {error_message}",
                            }
                        if isinstance(info, dict):
                            return {
                                "activity_results": [],
                                "response_text": (
                                    f"**{info.get('name')}**\n{info.get('description')}\n\n"
                                    "Want to add this to your plan?"
                                ),
                            }
            except Exception:
                pass
            return {
                "activity_results": [],
                "response_text": f"I couldn't find more info about {place_name_for_lookup} right now. Please try again shortly.",
            }

        city = state.get("city") or state.get("traveling_to_city")
        if city:
            resolved_city, err = validate_and_resolve_city(city)
            if err:
                return {
                    "activity_status": "CLARIFYING",
                    "response_text": err
                }
            city = resolved_city

        async with mcp_client.session("places") as session:
            place_tools = await load_mcp_tools(session)
            agent = llm.bind_tools(place_tools)

            city_hint = (
                f"The user recently booked travel to {city} - use that city if they don't mention a different one. "
                if city else ""
            )
            messages = [
                SystemMessage(content=(
                    "You are the places agent. Use search_places to find places to visit "
                    "in the city the user mentions. Supported categories: museums, attractions, "
                    "nature, nightlife, art, historic. Only set a category if the user specifically "
                    "asked for one (e.g. 'museums in Paris') - for a general 'things to do' request, "
                    "leave the category unset so you get a broad mix of results. "
                    f"{city_hint}"
                    "If no city is known at all, ask for one instead of guessing."
                )),
                *[HumanMessage(content=m) for m in state["messages"]],
            ]
            response = await agent.ainvoke(messages)

            if response.tool_calls:
                tool_call = response.tool_calls[0]
                matching_tool = next(t for t in place_tools if t.name == tool_call["name"])
                args = dict(tool_call["args"])
                if tool_call["name"] == "search_places" and not args.get("city") and city:
                    args["city"] = city

                raw_result = await matching_tool.ainvoke(args)
                result = _parse_mcp_result(raw_result)
                error_message = _extract_mcp_error(result)
                if error_message:
                    return {
                        "city": city,
                        "activity_results": [],
                        "response_text": f"I couldn't find places for that city - {error_message}"
                    }

                places = result if isinstance(result, list) else []
                return {
                    "city": city,
                    "activity_results": places,
                    "activity_search_cache": places,
                    "response_text": "",
                }
            return {"city": city, "response_text": response.content}
    except Exception:
        traceback.print_exc()
        return {
            "activity_results": [],
            "response_text": "The places service is currently unavailable. Please try again shortly."
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
        activity_type = state.get("activity_type")
        label = activity_type if activity_type else "things to do"
        lines = [_format_activity(place) for place in activity_results[:8]]
        return {
            "response_text": (
                f"Here are the {label} I found:\n" + "\n".join(lines)
                + "\n\nSee something you like? Say \" add [name] to my plan\" to save it"
            )
        }

def route_after_extraction(state: GraphState) -> str:
    intent = state.get("intent", "unknown")

    if intent in ("hotel","flight","weather","activities","itinerary"):
        return intent
    
    return "unknown"