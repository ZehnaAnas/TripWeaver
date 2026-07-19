from typing import Optional
from .constants import VALID_AIRPORTS,VALID_CITIES,CITY_TO_AIRPORT,COUNTRY_TO_CITIES
import difflib
import re
from datetime import datetime

def validate_and_resolve_city(input_city: str) -> tuple[Optional[str], Optional[str]]:
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