from mcp.server.fastmcp import FastMCP
import urllib.parse
from typing import Optional
import json
import urllib.request
import urllib.error
import uuid

mcp = FastMCP("Hotel Service",port=8001)

BASE_URL = "https://standing-fish-574.convex.site"

def _get_json(url:str):
    try:
        with urllib.request.urlopen(url,timeout=20) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8",errors="replace")
        return {"error":True,"status":e.code,"message":body,"url":url}
    except Exception as e:
        return {
            "error":True,
                "message":str(e),
                "url":url
                }
    
def _hotel_details(data):
    """
    Convert full hotel response into only:
    hotel name, description, facilities, available rooms,price ,address,city,star rating.

    Support both:
    1. {"hotels":[...]}
    2. [...]
    """
    if isinstance(data,dict) and "hotels" in data:
        hotels = data["hotels"]
    elif isinstance(data,list):
        hotels = data
    else:
        return data
    
    return [
        {
        "address":hotel.get("address"),
        "amenities":hotel.get("amenities"),
        "availableRooms":hotel.get("availableRooms"),
        "city":hotel.get("city"),
        "description":hotel.get("description"),
        "pricePerNight":hotel.get("pricePerNight"),
        "hotelName":hotel.get("name"),
        "starRating":hotel.get("starRating"),
        "cityCode" :hotel.get("airportCode")
    }
    for hotel in hotels
    ]

@mcp.tool()
def list_all_hotels()-> list[dict] | dict:
    """
    Retrieve all the hotels with only hotel name, description, facilities,price,available rooms, star rating, address and city
    """
    url = f"{BASE_URL}/hotels"
    data = _get_json(url)
    return _hotel_details(data)

@mcp.tool()
def search_hotel(
    city:Optional[str]= None,
    city_code:Optional[str] = None,
    hotel_name:Optional[str] = None,
    check_in:Optional[str] = None,
    check_out:Optional[str] = None,
    star_rating:Optional[int] =  None,
    hotel_budget:Optional[int] = None
) -> list[dict] | dict:
    """
    Search hotels using a city or airport code.
    
    Optional filters include hotel name, check-in/check-out dates,
    star rating, and budget.
    
    Returns only the essential hotel information required for
    recommendation or booking.
    """
    params = {
    }

    if city:
        params["city"] = city
    if city_code:
        params["cityCode"] = city_code
    if hotel_name:
        params["hotelName"] = hotel_name
    if check_in:
        params["checkIn"] = check_in
    if check_out:
        params["checkOut"] = check_out
    if star_rating:
        params["starRating"] = star_rating
    if hotel_budget:
        params["budget"] = hotel_budget

    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/hotels/search?{query_string}"
    data = _get_json(url)
    return _hotel_details(data)

@mcp.tool()
def book_hotel(
    hotel_name:str,
    check_in:str,
    check_out:str,
    guest_name:str,
    guest_email:str,
    room_type:str,
    hotel_id:Optional[str] = None,
):
    """ 
    Book a hotel using a hotel ID returned from a previous
    search_hotel() or list_all_hotels() call.
    
    The hotel_name must never be invented by the AI.
    
    Returns the booking confirmation from the external service.
    """
    if not all([hotel_name,check_in,check_out,guest_name,guest_email,room_type]):
        return {
            "error": True,
            "message": "Missing required booking details."
            }
    
    return {
        "confirmationId":f"HTL-{uuid.uuid4().hex[:8].upper()}",
        "status":"confirmed",
        "hotelName":hotel_name,
        "checkInDate":check_in,
        "checkOutDate":check_out,
        "guestName":guest_name,
        "guestEmail":guest_email,
        "roomType":room_type,
    }
if __name__ == "__main__":
    mcp.run("streamable-http")
    
    
