import json
import urllib.request
import urllib.parse
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Flight Service", port=8002)

BASE_URL = "https://standing-fish-574.convex.site"


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


def resolve_location(text: str):
    """
    Resolves a city name or airport code to an exact match.

    Returns:
      {"type": "city", "airport_code": "SIN", "city_name": "Singapore"}
        -> a single, exact city or airport code was found
      {"type": "unknown"}
        -> we couldn't match anything

    Country names are deliberately NOT supported - only an exact city name
    or a 3-letter airport code. This keeps every search unambiguous: one
    origin, one destination, one clear result, rather than silently
    expanding into several cities and reporting a confusing blanket
    "nothing found" if some of them have no matching flights.
    """
    if not text:
        return {"type": "unknown"}

    cleaned = text.strip()
    cleaned_lower = cleaned.lower()

    for city_name in VALID_CITIES:
        if city_name.lower() == cleaned_lower:
            return {
                "type": "city",
                "airport_code": CITY_TO_AIRPORT[city_name],
                "city_name": city_name,
            }

    for city_name, code in CITY_TO_AIRPORT.items():
        if code.lower() == cleaned_lower:
            return {
                "type": "city",
                "airport_code": code,
                "city_name": city_name,
            }

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
def _post_json(url: str, payload: dict):
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"error": True, "message": str(e), "url": url}

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
                         flight_date: Optional[str]):
    """
    Does one actual search against Convex, using resolved airport codes.
    Returns a list of simplified flight dicts (may be empty).
    """
    params = {}
    if origin_code:
        params["origin"] = origin_code
    if destination_code:
        params["destination"] = destination_code
    if flight_date:
        params["date"] = flight_date

    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/flights/search?{query_string}"

    data = _get_json(url)
    if isinstance(data, dict) and data.get("error"):
        return [] 

    result = _only_airline_origin_destination(data)
    if not isinstance(result, list):
        return []

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
) -> list[dict] | dict:
    """
    Search flights between an origin and a destination.

    Both origin and destination must be EITHER a city name (e.g.
    "Singapore", "Kuala Lumpur") OR a 3-letter airport code (e.g. "SIN",
    "KUL") - country names are not supported, only an exact city or code.

    flight_date is an optional filter - only apply it if the user
    actually asked for a specific date.

    If a city/code isn't recognized, this returns a helpful error dict
    instead of failing silently - always check for an "error" key in the
    result before treating it as a flight list.
    """
    origin_info = resolve_location(origin) if origin else {"type": "unknown"}
    destination_info = resolve_location(destination) if destination else {"type": "unknown"}

    if origin and origin_info["type"] == "unknown":
        return {
            "error": True,
            "message": f"I don't recognize '{origin}' as a city or airport code. "
                       f"Try a city like Singapore, Tokyo, or Bangkok.",
        }
    if destination and destination_info["type"] == "unknown":
        return {
            "error": True,
            "message": f"I don't recognize '{destination}' as a city or airport code. "
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

    origin_code = origin_info["airport_code"] if origin_info["type"] == "city" else None
    destination_code = destination_info["airport_code"] if destination_info["type"] == "city" else None

    all_results = _call_convex_search(origin_code, destination_code, flight_date)

    if len(all_results) == 0:
        origin_text = origin_info.get("city_name", "your starting point")
        destination_text = destination_info.get("city_name", "your destination")

        return {
            "error": True,
            "message": f"I couldn't find any flights from {origin_text} to {destination_text} right now. "
                       f"Try a different route or date.",
        }

    return all_results

@mcp.tool()
def book_flight(
    flight_id: str,
    passenger_name: str,
    passenger_email: str,
    flight_date:str,
    flying_type: str,
) -> dict:
    """
    Book a flight using a flight_id from a previous search_flights() or
    get_all_flights() result. flight_id must never be invented by the AI.
    Returns the real booking confirmation from the external service.
    """
    if not all([flight_id, passenger_name, passenger_email, flying_type,flight_date]):
        return {"error": True, "message": "Missing required booking details."}

    payload = {
        "flightId": flight_id,
        "passengerNames": passenger_name,
        "passengerEmails": passenger_email,
        "flightDate":flight_date,
        "flyingType": flying_type,
    }
    url = f"{BASE_URL}/flights/book"
    return _post_json(url, payload)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")