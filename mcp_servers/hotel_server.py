from mcp.server.fastmcp import FastMCP
import urllib.parse
from typing import Optional
import json
import urllib.request
import urllib.error

mcp = FastMCP("Hotel Service", port=8001)

BASE_URL = "https://standing-fish-574.convex.site"

AIRPORT_TO_CITY = {
    'DPS': 'Bali', 'BKK': 'Bangkok', 'PEK': 'Beijing', 'PUS': 'Busan',
    'CEB': 'Cebu', 'DEL': 'Delhi', 'CAN': 'Guangzhou', 'HAN': 'Hanoi',
    'SGN': 'Ho Chi Minh City', 'CGK': 'Jakarta', 'KUL': 'Kuala Lumpur',
    'MNL': 'Manila', 'BOM': 'Mumbai', 'KIX': 'Osaka', 'PEN': 'Penang',
    'HKT': 'Phuket', 'ICN': 'Seoul', 'PVG': 'Shanghai', 'SIN': 'Singapore',
    'NRT': 'Tokyo',
}


def _resolve_city(city: Optional[str]) -> Optional[str]:
    if not city:
        return None
    cleaned = city.strip()
    if (len(cleaned) == 3 and cleaned.isalpha()):
        return AIRPORT_TO_CITY.get(
            cleaned.upper(),
            cleaned
        )
    return cleaned

def _get_json(url: str):
    try:
        with urllib.request.urlopen(url,timeout=20) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8",errors="replace")
        return {
            "error": True,
            "status": e.code,
            "message": body,
            "url": url
        }
    except Exception as e:
        return {
            "error": True,
            "message": str(e),
            "url": url
        }

def _post_json(url: str,payload: dict):
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type":
                "application/json"
            },
            method="POST",
        )
        with urllib.request.urlopen(req,timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8",errors="replace")
        return {
            "error": True,
            "status": e.code,
            "message": body,
            "url": url
        }
    except Exception as e:
        return {
            "error": True,
            "message": str(e),
            "url": url
        }

def _hotel_details(data):
    if (isinstance(data, dict) and "hotels" in data):
        hotels = data["hotels"]
    elif isinstance(data, list):
        hotels = data
    else:
        return data
    simplified_hotels = []
    for hotel in hotels:
        simplified_hotels.append({
            "hotelId":hotel.get("_id"),
            "address":hotel.get("address"),
            "amenities":hotel.get("amenities"),
            "availableRooms":hotel.get("availableRooms"),
            "city":hotel.get("city"),
            "description":hotel.get("description"),
            "pricePerNight":hotel.get("pricePerNight"),
            "hotelName":hotel.get("name"),
            "starRating":hotel.get("starRating"),
        })
    return simplified_hotels

@mcp.tool()
def list_all_hotels() -> list[dict] | dict:
    """
    Get a list of all available hotels.
    Use this when the user asks to show/list all hotels.
    """
    url = (f"{BASE_URL}/hotels")
    data = _get_json(url)
    return _hotel_details(data)

@mcp.tool()
def search_hotel(
    city: Optional[str] = None,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
) -> list[dict] | dict:
    """
    Search hotels by city (a name like "Kuala Lumpur" OR a 3-letter
    airport code like "KUL" both work), by hotel name, or both together.
    check_in, check_out dates are optional.
    Only returns hotels that actually have at least one available room.
    """
    resolved_city = _resolve_city(city)
    params = {}
    if resolved_city:
        params["city"] = (resolved_city)
    if check_in:
        params["checkIn"] = (check_in)
    if check_out:
        params["checkOut"] = (check_out)
    if params:
        url = (f"{BASE_URL}/hotels/search?"
               f"{urllib.parse.urlencode(params)}"
               )
    else:
        url = (f"{BASE_URL}/hotels")
    data = _get_json(url)
    hotels = _hotel_details(data)
    if not isinstance(hotels,list):
        return hotels
    hotels = [hotel for hotel in hotels if (hotel.get("availableRooms") or 0) > 0]
    return hotels

@mcp.tool()
def book_hotel(
    hotel_id: str,
    check_in: str,
    check_out: str,
    guest_name: str,
    guest_email: str,
    room_type: str,
) -> dict:
    """
    Book a hotel room.

    Requires:
    - hotel_id
    - check_in
    - check_out
    - guest_name
    - guest_email
    - room_type

    The booking is sent directly to the hotel API.
    """
    payload = {
        "hotelId":hotel_id,
        "checkInDate":check_in,
        "checkOutDate":check_out,
        "guestName":guest_name,
        "guestEmail":guest_email,
        "roomType":room_type,
    }
    url = f"{BASE_URL}/hotels/book"
    result = _post_json(url,payload)
    return result


if __name__ == "__main__":
    mcp.run("streamable-http")