from mcp.server.fastmcp import FastMCP
import urllib.parse
from typing import Optional
import json
import urllib.request
import urllib.error

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
def _post_json(url:str, payload:dict):
    try:
        data = json.dumps(payload).encode("utf-8")
        req= urllib.request.Request(
            url,data = data,
            headers = {"Content-Type":"application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req,timeout=20) as response:
            details = response.read().decode("utf-8")
            return json.loads(details)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8",errors="replace")
        return {"error":True,"status":e.code,"message":body,"url":url}
    except Exception as e:
        return {"error":True,
                "message":str(e),
                "url":url}
    
def _hotel_details(data):
    if isinstance(data,dict) and "hotels" in data:
        hotels = data["hotels"]
    elif isinstance(data,list):
        hotels = data
    else:
        return data
    
    return [
        {
        "hotelID":hotel.get("_id"),
        "address":hotel.get("address"),
        "facilities":hotel.get("amenities"),
        "availableRooms":hotel.get("availableRooms"),
        "city":hotel.get("city"),
        "description":hotel.get("description"),
        "pricePerNight":hotel.get("pricePerNight"),
        "name":hotel.get("name"),
        "starRating":hotel.get("starRating")
    }
    for hotel in hotels
    ]

@mcp.tool()
def list_all_hotels()-> list[dict] | dict:
    """
    Return all the hotel information when the user asks to list all the hotels available
    """
    url = f"{BASE_URL}/hotels"
    data = _get_json(url)
    return _hotel_details(data)

@mcp.tool()
def search_hotel(
    city:str,
    name:Optional[str] = None,
    checkIn:Optional[str] = None,
    checkOut:Optional[str] = None,
    starRating:Optional[str] =  None,
    amenities:Optional[str]=None,
    budget:Optional[str] = None
) -> list[dict] | dict:
    """
    Search hotels by using only city.
    Return only the hotel id,hotel name, description, address, price per night , available rooms, amenities and star rating.
    """
    params = {
        "city":city,
    }
    
    if name:
        params["name"] = name
    if checkIn:
        params["checkIn"] = checkIn
    if checkOut:
        params["checkOut"] = checkOut
    if starRating:
        params["starRating"] = starRating
    if amenities:
        params["amenities"] = amenities
    if budget:
        params["budget"] = budget

    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/hotels/search?{query_string}"
    data = _get_json(url)
    return _hotel_details(data)

@mcp.tool()
def book_hotel(
    hotelId:str,
    checkIn:str,
    checkOut:str,
    name:str,
    email:str,
    roomType:str
):
    payload = {
        
        "hotelId":hotelId,
        "checkInDate":checkIn,
        "checkOutDate":checkOut,
        "guestName":name,
        "guestEmail":email,
        "roomType":roomType
    }

    url = f"{BASE_URL}/hotels/book"
    data = _post_json(url,payload)
    return data

if __name__ == "__main__":
    mcp.run("streamable-http")
    
    
