import json
import urllib.request
import urllib.parse
from typing import Optional
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("Flight Service", port=8002)


BASE_URL = "https://standing-fish-574.convex.site"


def _get_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    except Exception as e:
        return {"error": True, "message": str(e), "url": url}


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
            "flightId": flight.get("_id"),
            "airline": flight.get("airline"),
            "originCity": origin_info.get("city"),
            "originAirport": origin_info.get("airport"),
            "destinationCity": destination_info.get("city"),
            "destinationAirport": destination_info.get("airport"),
            "price": flight.get("price"),
            "departureTime": flight.get("departureTime"),
            "arrivalTime": flight.get("arrivalTime"),
            "availableSeats": flight.get("availableSeats"),
            "flightDate": flight.get("flightDate"),
            "flightNumber": flight.get("flightNumber"),
        })

    return simplified_flights


@mcp.tool()
def get_all_flights() -> list[dict] | dict:
    """
    Retrieve all available flights.
    Use this when the user explicitly asks to: 
    - show all flights 
    - list all flights 
    - see available flights
    """
    url = f"{BASE_URL}/flights"
    data = _get_json(url)
    flights = _only_airline_origin_destination(data)
    if not isinstance( flights, list ): 
        return flights
    return flights

@mcp.tool()
def search_flights(
    origin: str,
    destination: str,
    flight_date: Optional[str] = None,
) -> list[dict] | dict:
    """
    Search flights between an origin and destination. 
    origin and destination can be: 

    - City names 
    - 3-letter airport codes 

    date is optional
    """
    
    normalized_origin = origin.upper() if origin and len(origin) == 3 and origin.isalpha() else origin
    normalized_destination = destination.upper() if destination and len(destination) == 3 and destination.isalpha() else destination
    params = {"origin": normalized_origin, "destination": normalized_destination}
    if flight_date:
        params["date"] = flight_date

    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/flights/search?"f"{query_string}"

    data = _get_json(url)
    flights = (_only_airline_origin_destination(data))
    return flights

@mcp.tool()
def book_flight(
    flight_id: str,
    passenger_name: str,
    passenger_email: str,
) -> dict:
    """
    Book a flight.
    flight_id must come from a real flight returned by: 
    - search_flights() 
    - get_all_flights() 
    The AI must NEVER invent a flight_id.
    """
    payload = {
        "flightId": flight_id,
        "passengerNames": passenger_name,
        "passengerEmails": passenger_email,
    }
    url = f"{BASE_URL}/flights/book"
    result = _post_json(url, payload)
    if isinstance( result, dict ) and result.get( "error" ):
        return result
    return result
    

if __name__ == "__main__":
    mcp.run(transport="streamable-http")