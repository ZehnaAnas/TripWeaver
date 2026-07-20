from mcp.server.fastmcp import FastMCP
import urllib.parse
from typing import Optional
import json
import urllib.request
import urllib.error


mcp = FastMCP("Hotel Service", port=8001)

BASE_URL = "https://standing-fish-574.convex.site"


def _get_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": True, "status": e.code, "message": body, "url": url}
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
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": True, "status": e.code, "message": body, "url": url}
    except Exception as e:
        return {"error": True, "message": str(e), "url": url}
    
def _hotel_details(data):
    if isinstance(data, dict) and "hotels" in data:
        hotels = data["hotels"]
    elif isinstance(data, list):
        hotels = data
    else:
        return data

    simplified_hotels = []
    for hotel in hotels:
        simplified_hotels.append({
            "hotelId": hotel.get("_id"),
            "address": hotel.get("address"),
            "amenities": hotel.get("amenities"),
            "availableRooms": hotel.get("availableRooms"),
            "city": hotel.get("city"),
            "description": hotel.get("description"),
            "pricePerNight": hotel.get("pricePerNight"),
            "hotelName": hotel.get("name"),
            "starRating": hotel.get("starRating"),
        })
    return simplified_hotels


@mcp.tool()
def list_all_hotels() -> list[dict] | dict:
    """
    Retrieve all the hotels with only hotel id, name, description,
    facilities, price, available rooms, star rating, address and city.
    """
    url = f"{BASE_URL}/hotels"
    data = _get_json(url)
    return _hotel_details(data)


@mcp.tool()
def search_hotel(
    city: str,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
) -> list[dict] | dict:
    """
    Search hotels by city , with optional check-in/check-out dates.

    Returns only the essential hotel information required for
    recommendation or booking.
    """
    params = {"city":city}

    if check_in:
        params["checkIn"] = check_in
    if check_out:
        params["checkOut"] = check_out

    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/hotels/search?{query_string}"
    data = _get_json(url)
    hotels = _hotel_details(data)

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
    Book a hotel using a hotelId from a previous search_hotel() or
    list_all_hotels() result. hotel_id must never be invented by the AI -
    it must be copied exactly from a real search result.
    """

    payload = {
        "hotelId": hotel_id,
        "checkInDate": check_in,
        "checkOutDate": check_out,
        "guestName": guest_name,
        "guestEmail": guest_email,
        "roomType": room_type,
    }
    url = f"{BASE_URL}/hotels/book"
    return _post_json(url, payload)

if __name__ == "__main__":
    mcp.run("streamable-http")