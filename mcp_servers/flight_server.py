import json
import urllib.request
import urllib.parse
from typing import Optional
from mcp.server.fastmcp import FastMCP
import uuid

mcp = FastMCP("Flight Service", port=8002)

BASE_URL = "https://standing-fish-574.convex.site/flights"

# This server runs as its own separate process, so it can't import anything
# from agents/nodes.py - we keep our own small copy of the city data here.

VALID_CITIES = [
    'Bali', 'Bangkok', 'Beijing', 'Busan', 'Cebu', 'Delhi', 'Guangzhou',
    'Hanoi', 'Ho Chi Minh City', 'Jakarta', 'Kuala Lumpur', 'Manila',
    'Mumbai', 'Osaka', 'Penang', 'Phuket', 'Seoul', 'Shanghai',
    'Singapore', 'Tokyo'
]

CITY_TO_AIRPORT = {
    'Bali': 'DPS', 'Bangkok': 'BKK', 'Beijing': 'PEK', 'Busan': 'PUS',
    'Cebu': 'CEB', 'Delhi': 'DEL', 'Guangzhou': 'CAN', 'Hanoi': 'HAN',
    'Ho Chi Minh City': 'SGN', 'Jakarta': 'CGK', 'Kuala Lumpur': 'KUL',
    'Manila': 'MNL', 'Mumbai': 'BOM', 'Osaka': 'KIX', 'Penang': 'PEN',
    'Phuket': 'HKT', 'Seoul': 'ICN', 'Shanghai': 'PVG', 'Singapore': 'SIN',
    'Tokyo': 'NRT',
}

COUNTRY_TO_CITIES = {
    "indonesia": ["Bali", "Jakarta"],
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


def resolve_location(text: str):
    """
    Figures out what kind of place the user typed.

    Returns a dictionary describing what we found:
      {"type": "city", "airport_code": "SIN", "city_name": "Singapore"}
        -> a single, exact city or airport code was found

      {"type": "country", "country_name": "Thailand", "cities": ["Bangkok", "Phuket"]}
        -> a country name was found; here are the cities in it we support

      {"type": "unknown"}
        -> we couldn't match anything
    """
    if not text:
        return {"type": "unknown"}

    cleaned = text.strip()
    cleaned_lower = cleaned.lower()

    # Step 1: is it an exact city name? Check this FIRST - some places
    # (like Singapore) are both a country name and a city name, and if
    # someone just types "Singapore" they clearly mean the city, not
    # "search every city in the country of Singapore".
    for city_name in VALID_CITIES:
        if city_name.lower() == cleaned_lower:
            return {
                "type": "city",
                "airport_code": CITY_TO_AIRPORT[city_name],
                "city_name": city_name,
            }

    # Step 2: is it an exact airport code? (also fine, totally optional)
    for city_name, code in CITY_TO_AIRPORT.items():
        if code.lower() == cleaned_lower:
            return {
                "type": "city",
                "airport_code": code,
                "city_name": city_name,
            }

    # Step 3: is it a country name?
    if cleaned_lower in COUNTRY_TO_CITIES:
        cities_in_country = COUNTRY_TO_CITIES[cleaned_lower]
        return {
            "type": "country",
            "country_name": cleaned.title(),
            "cities": cities_in_country,
        }

    # Step 4: nothing matched.
    return {"type": "unknown"}


def _get_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    except Exception as e:
        return {
            "error": True,
            "message": str(e),
            "url": url,
        }


def _only_airline_origin_destination(data):
    """
    Convert a full flight response into just the fields we actually need:
    id, price, times, seats, airline, origin/destination city+country+airport.

    Supports two possible response shapes from Convex:
      1. {"flights": [...]}
      2. [...]
    """
    if isinstance(data, dict) and "flights" in data:
        flights = data["flights"]
    elif isinstance(data, list):
        flights = data
    else:
        return data

    simplified_flights = []
    for flight in flights:
        origin_info = flight.get("origin", {})
        destination_info = flight.get("destination", {})

        simplified_flights.append({
            "airline": flight.get("airline"),
            "originCity": origin_info.get("city"),
            "originCountry": origin_info.get("country"),
            "originAirport": origin_info.get("airport"),
            "destinationCity": destination_info.get("city"),
            "destinationCountry": destination_info.get("country"),
            "destinationAirport": destination_info.get("airport"),
            "flightId": flight.get("_id"),
            "price": flight.get("price"),
            "departureTime": flight.get("departureTime"),
            "arrivalTime": flight.get("arrivalTime"),
            "availableSeats": flight.get("availableSeats"),
            "flightDate": flight.get("flightDate"),
            "flightNumber": flight.get("flightNumber"),
        })

    return simplified_flights


def _call_convex_search(origin_code: Optional[str], destination_code: Optional[str],
                         flight_date: Optional[str], flight_budget: Optional[int]):
    """
    Does one actual search against Convex, using resolved airport codes.
    Returns a list of simplified flight dicts (may be empty).

    NOTE: we send flight_budget to Convex as a filter, but Convex does NOT
    reliably filter by it (confirmed by testing - flights well over budget
    still came back). So we ALSO filter by budget ourselves below, after
    getting the results back. This guarantees the budget is actually
    respected regardless of what Convex does with it.
    """
    params = {}
    if origin_code:
        params["origin"] = origin_code
    if destination_code:
        params["destination"] = destination_code
    if flight_date:
        params["date"] = flight_date
    if flight_budget:
        params["budget"] = flight_budget

    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/flights/search?{query_string}"

    data = _get_json(url)
    if isinstance(data, dict) and data.get("error"):
        return []  # treat a request error as "no results found", not a crash

    result = _only_airline_origin_destination(data)
    if not isinstance(result, list):
        return []

    # Do our own budget filtering here, since Convex's own filtering can't
    # be trusted to actually apply it.
    if flight_budget:
        filtered_result = []
        for flight in result:
            price = flight.get("price")
            if price is not None and price <= flight_budget:
                filtered_result.append(flight)
        return filtered_result

    return result


@mcp.tool()
def get_all_flights() -> list[dict] | dict:
    """
    Retrieve all flights with id, price, times, seats, airline, origin/destination
    city, country, and airport, and flight date.
    """
    url = f"{BASE_URL}/flights"
    data = _get_json(url)
    return _only_airline_origin_destination(data)


@mcp.tool()
def search_flights(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    flight_date: Optional[str] = None,
    flight_budget: Optional[int] = None,
    departure_time: Optional[str] = None,
) -> list[dict] | dict:
    """
    Search flights between an origin and a destination.

    Both origin and destination accept EITHER a city name (e.g. "Singapore",
    "Kuala Lumpur") OR a 3-letter airport code (e.g. "SIN", "KUL") - city
    names are preferred and don't need a code.

    You can also pass a country name (e.g. "Thailand") instead of a specific
    city - in that case, this searches every city we support in that country
    and returns all matching flights, tagged by which city they're for.

    flight_date, flight_budget, and departure_time (e.g. "06:30") are all
    optional filters - only apply them if the user actually asked for them.

    If a city/country/code isn't recognized, this returns a helpful error
    dict instead of failing silently - always check for an "error" key in
    the result before treating it as a flight list.
    """
    origin_info = resolve_location(origin) if origin else {"type": "unknown"}
    destination_info = resolve_location(destination) if destination else {"type": "unknown"}

    if origin and origin_info["type"] == "unknown":
        return {
            "error": True,
            "message": f"I don't recognize '{origin}' as a city, airport code, or country. "
                       f"Try a city like Singapore, Tokyo, or Bangkok.",
        }
    if destination and destination_info["type"] == "unknown":
        return {
            "error": True,
            "message": f"I don't recognize '{destination}' as a city, airport code, or country. "
                       f"Try a city like Singapore, Tokyo, or Bangkok.",
        }

    if origin and not destination:
        return {
            "error": True,
            "message": "Which city would you like to fly to?",
        }
    if destination and not origin:
        return {
            "error": True,
            "message": "Which city would you like to fly from?",
        }

    origin_codes = []
    if origin_info["type"] == "city":
        origin_codes = [origin_info["airport_code"]]
    elif origin_info["type"] == "country":
        for city_name in origin_info["cities"]:
            origin_codes.append(CITY_TO_AIRPORT[city_name])
    else:
        origin_codes = [None]

    destination_codes = []
    if destination_info["type"] == "city":
        destination_codes = [destination_info["airport_code"]]
    elif destination_info["type"] == "country":
        for city_name in destination_info["cities"]:
            destination_codes.append(CITY_TO_AIRPORT[city_name])
    else:
        destination_codes = [None]

    all_results = []
    for one_origin_code in origin_codes:
        for one_destination_code in destination_codes:
            results_for_this_pair = _call_convex_search(
                one_origin_code, one_destination_code, flight_date, flight_budget
            )
            all_results.extend(results_for_this_pair)

    # Apply the departure-time filter ourselves, locally - same reasoning
    # as budget: we don't trust the external service to actually filter
    # by this, even if it accepted the parameter.
    if departure_time and isinstance(all_results, list):
        all_results = [f for f in all_results if f.get("departureTime") == departure_time]

    if len(all_results) == 0:
        if origin_info["type"] == "country":
            searched_places = f"cities in {origin_info['country_name']}"
        elif origin_info["type"] == "city":
            searched_places = origin_info["city_name"]
        else:
            searched_places = "your starting point"

        if destination_info["type"] == "country":
            searched_places += f" to cities in {destination_info['country_name']}"
        elif destination_info["type"] == "city":
            searched_places += f" to {destination_info['city_name']}"

        filter_notes = []
        if flight_budget:
            filter_notes.append(f"under ${flight_budget}")
        if departure_time:
            filter_notes.append(f"departing at {departure_time}")
        filter_text = " ".join(filter_notes)

        return {
            "error": True,
            "message": f"I couldn't find any flights from {searched_places} {filter_text} right now. "
                       f"Try a different route, date, budget, or time.",
        }

    origin_was_country = origin_info["type"] == "country"
    destination_was_country = destination_info["type"] == "country"

    if origin_was_country or destination_was_country:
        if origin_was_country:
            origin_cities_text = ", ".join(origin_info["cities"])
        else:
            origin_cities_text = origin_info.get("city_name", "your origin")

        if destination_was_country:
            destination_cities_text = ", ".join(destination_info["cities"])
        else:
            destination_cities_text = destination_info.get("city_name", "your destination")

        note = (
            f"These results cover multiple cities ({origin_cities_text} → "
            f"{destination_cities_text}). Which city would you like to fly "
            f"from, and which city would you like to fly to?"
        )
        return {"flights": all_results, "note": note}

    return all_results

@mcp.tool()
def book_flight(
    passenger_name: str,
    passenger_email: str,
    flying_type: str,
    date_of_birth: str,
    passport_number: str,
    nationality: str,
    airline: str,
) -> dict:
    """
    Confirms a flight booking. Airline must never be invented by the AI -
    it must come from a previous search_flights() or get_all_flights() result.
    """
    if not all([airline, passenger_name, passenger_email, flying_type,
                date_of_birth, passport_number, nationality]):
        return {"error": True, "message": "Missing required booking details."}

    return {
        "confirmationId": f"FLT-{uuid.uuid4().hex[:8].upper()}",
        "status": "confirmed",
        "airline": airline,
        "passengerName": passenger_name,
        "passengerEmail": passenger_email,
        "flyingType": flying_type,
        "dateOfBirth": date_of_birth,
        "passportNumber": passport_number,
        "nationality": nationality,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")