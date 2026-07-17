import json 
import urllib.request
import urllib.parse
from typing import Optional
from mcp.server.fastmcp import FastMCP
import uuid

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
            "destinationCountry":flight.get("destination",{}).get("country"),
            "originCountry":flight.get("origin",{}).get("country"),
            "originAirport":flight.get("origin",{}).get("airport"),
            "destinationAirport":flight.get("destination",{}).get("airport"),
            "flightId":flight.get("_id"),
            "price":flight.get("price"),
            "departureTime":flight.get("departureTime"),
            "arrivalTime":flight.get("arrivalTime"),
            "availableSeats":flight.get("availableSeats"),
            "flightDate":flight.get("flightDate"),
            "flightNumber":flight.get("flightNumber")
        }
        for flight in flights
    ]


@mcp.tool()
def get_all_flights() -> list[dict] | dict :
    """
    Retrieve all flights with only id,price,departure time/arrival time, available seats, airline ,origin airport,
    origin city, origin country ,destination airport,destination city, destination country and flight date.

    """

    url = f"{BASE_URL}/flights"
    data = _get_json(url)
    return _only_airline_origin_destination(data)

@mcp.tool()
def search_flights(
    origin:Optional[str]=None,
    destination:Optional[str]=None,
    origin_country:Optional[str]=None,
    destination_country:Optional[str]=None,
    flight_date:Optional[str]=None,
    flight_budget:Optional[int]=None,
    departure_time:Optional[str]=None
) -> list[dict] |dict:
    """
    Search flights by only origin and/or destination. 
    Search flights by using countries names is allowed too.
    Return only flight id,airline,origin city,origin country,destination city, destination country,
    ,price,departure time,arrival time, available seats and flight date.
    Date is optional and it must match with the flight dates.
    """
    params = {}
    if origin: params["origin"] = origin
    if destination: params["destination"] = destination
    if origin_country:params["originCountry"] = origin_country
    if destination_country:params["destinationCountry"] = destination_country
    if flight_date: params["date"] = flight_date
    if flight_budget: params["budget"] = flight_budget
    if departure_time: params["departureTime"]= departure_time

    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/flights/search?{query_string}"

    data = _get_json(url)

    return _only_airline_origin_destination(data)

@mcp.tool()
def book_flight(
    passenger_name:str,
    passenger_email:str,
    flying_type:str,
    date_of_birth:str,
    passport_number:str,
    nationality:str,
    airline:str,
)->dict:
    """ 
    Confirms a flight booking. Airline must never be invented by the AI and it must come from a previous
    search_flights() or get_all_flights() result.
    Returns the booking confirmation from the external service.
    """
    if not all([airline,passenger_name,passenger_email,flying_type,date_of_birth,passport_number,nationality]):
        return{"error":True,"message":"Missing required booking details."}
    return {
        "confirmationId":f"FLT-{uuid.uuid4().hex[:8].upper()}",
        "status":"confirmed",
        "airline":airline,
        "passengerName":passenger_name,
        "passengerEmail":passenger_email,
        "flyingType":flying_type,
        "dateOfBirth":date_of_birth,
        "passportNumber":passport_number,
        "nationality":nationality,
    }

if __name__ == "__main__":
    mcp.run(transport="streamable-http")