import json 
import urllib.request
import urllib.parse
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Flight Service",port = 8002)

BASE_URL = "https://standing-fish-574.convex.site"

def _get_json(url:str):
    try:
        with urllib.request.urlopen(url,timeout=20) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    except Exception as e:
        return {
            "error":True,
            "message":str(e),
            "url":url
        }
    
def _post_json(url:str , payload:dict):
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data = data,
            headers={"Content-Type":"application/json"},
            method = "POST"
        )
        with urllib.request.urlopen(req,timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {
            "error":True,
            "message":str(e),
            "url":url
        }
    
def  _only_airline_origin_destination(data):
    """
    Convert full flight response into only:
    id,price,departure time/arrival time, available seats airline, origin city, destination city.

    Support both:
    1. {"flights":[...]}
    2. [...]
    """
    if isinstance(data,dict) and "flights" in data:
        flights = data["flights"]
    elif isinstance(data,list):
        flights = data
    else:
        return data
    
    return [
        {
            "airline":flight.get("airline"),
            "originCity":flight.get("origin",{}).get("city"),
            "destinationCity":flight.get("destination",{}).get("city"),
            "id":flight.get("_id"),
            "price":flight.get("price"),
            "departureTime":flight.get("departureTime"),
            "arrivalTime":flight.get("arrivalTime"),
            "availableSeats":flight.get("availableSeats"),
            "flightDate":flight.get("flightDate")
        }
        for flight in flights
    ]


@mcp.tool()
def get_all_flights() -> list[dict] | dict :
    """
    Retrieve all flights with only id,price,departure time/arrival time, available seats airline, origin city, destination city and flight date.

    """

    url = f"{BASE_URL}/flights"
    data = _get_json(url)
    return _only_airline_origin_destination(data)

@mcp.tool()
def search_flights(
    origin:str,
    destination:str,
    date:Optional[str]=None
) -> list[dict] |dict:
    """
    Search flights by origin and destination.
    Return only airline,origin city,destination city,flight id,price,departure time,arrival time, available seats and flight date.
    Date is optional and when given it must match with the flight dates.
    """
    params = {
        "origin":origin,
        "destination":destination,
    }

    if date:
        params["date"] = date

    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/flights/search?{query_string}"

    data = _get_json(url)

    return _only_airline_origin_destination(data)

@mcp.tool()
def book_flight(
    passenger_email:str,
    passenger_name:str,
    flight_id:str
)->dict:
    """ 
    Book a flight by it's flight ID.
    Ensure it's ID must come from a prior search_flights or get_all_flights result, and never invent one.
    Return only the booking confirmation.
    """
    payload = {
        "flightId":flight_id,
        "passengerName":passenger_name,
        "passengerEmail":passenger_email,
    }

    url = f"{BASE_URL}/flights/book"
    data = _post_json(url,payload)
    return data

if __name__ == "__main__":
    mcp.run(transport="streamable-http")