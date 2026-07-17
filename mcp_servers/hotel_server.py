from mcp.server.fastmcp import FastMCP
import urllib.parse
from typing import Optional
import json
import urllib.request
import urllib.error
import uuid

mcp = FastMCP("Hotel Service", port=8001)

BASE_URL = "https://standing-fish-574.convex.site"

# Lets the search tool accept an airport code (like "PUS") for city_code and
# turn it into the real city name ("Busan") that Convex's /hotels endpoint
# actually understands.
AIRPORT_TO_CITY = {
    'DPS': 'Bali', 'BKK': 'Bangkok', 'PEK': 'Beijing', 'PUS': 'Busan',
    'CEB': 'Cebu', 'DEL': 'Delhi', 'CAN': 'Guangzhou', 'HAN': 'Hanoi',
    'SGN': 'Ho Chi Minh City', 'CGK': 'Jakarta', 'KUL': 'Kuala Lumpur',
    'MNL': 'Manila', 'BOM': 'Mumbai', 'KIX': 'Osaka', 'PEN': 'Penang',
    'HKT': 'Phuket', 'ICN': 'Seoul', 'PVG': 'Shanghai', 'SIN': 'Singapore',
    'NRT': 'Tokyo',
}


def _get_json(url: str):
    """Fetches a URL and parses it as JSON. Never raises - always returns
    either the parsed data, or a small {"error": True, ...} dict."""
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": True, "status": e.code, "message": body, "url": url}
    except Exception as e:
        return {"error": True, "message": str(e), "url": url}


def _hotel_details(data):
    """
    Convert the full hotel response from Convex into just the fields we
    need: hotel name, description, amenities, available rooms, price,
    address, city, and star rating.

    Handles two possible response shapes from Convex:
      1. {"hotels": [...]}
      2. [...]
    """
    if isinstance(data, dict) and "hotels" in data:
        hotels = data["hotels"]
    elif isinstance(data, list):
        hotels = data
    else:
        return data

    simplified_hotels = []
    for hotel in hotels:
        simplified_hotels.append({
            "address": hotel.get("address"),
            "amenities": hotel.get("amenities"),
            "availableRooms": hotel.get("availableRooms"),
            "city": hotel.get("city"),
            "description": hotel.get("description"),
            "pricePerNight": hotel.get("pricePerNight"),
            "hotelName": hotel.get("name"),
            "starRating": hotel.get("starRating"),
            "cityCode": hotel.get("airportCode"),
        })
    return simplified_hotels


def _apply_local_filters(hotels, hotel_budget=None, star_rating=None, hotel_name=None):
    """
    Filters an already-fetched list of hotels by hotel name, budget, and/or
    star rating.

    We do all of this filtering ourselves, in plain Python, instead of
    trusting Convex's own hotelName/budget/starRating query parameters -
    testing showed those parameters don't reliably filter server-side
    (e.g. searching for "Shangri-La" returned every hotel in the city, not
    just the Shangri-La ones). Doing it here guarantees each filter is
    actually respected.
    """
    filtered = hotels

    if hotel_name:
        query = hotel_name.strip().lower()
        filtered = [
            hotel for hotel in filtered
            if query in (hotel.get("hotelName") or "").lower()
        ]

    if hotel_budget:
        filtered = [
            hotel for hotel in filtered
            if hotel.get("pricePerNight") is not None and hotel.get("pricePerNight") <= hotel_budget
        ]

    if star_rating:
        filtered = [
            hotel for hotel in filtered
            if hotel.get("starRating") == star_rating
        ]

    return filtered


@mcp.tool()
def list_all_hotels() -> list[dict] | dict:
    """
    Retrieve all the hotels with only hotel name, description, facilities,
    price, available rooms, star rating, address and city.
    """
    url = f"{BASE_URL}/hotels"
    data = _get_json(url)
    return _hotel_details(data)


@mcp.tool()
def search_hotel(
    city: Optional[str] = None,
    city_code: Optional[str] = None,
    hotel_name: Optional[str] = None,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
    star_rating: Optional[int] = None,
    hotel_budget: Optional[int] = None,
) -> list[dict] | dict:
    """
    Search hotels using a city or airport code.

    Optional filters include hotel name, check-in/check-out dates, star
    rating, and budget. Hotel name, budget, and star rating are all
    enforced locally (see _apply_local_filters) since the external service
    doesn't reliably apply any of them itself.

    Returns only the essential hotel information required for
    recommendation or booking.
    """
    # Accept an airport code for city_code and turn it into a real city
    # name, since Convex's /hotels endpoint only understands city names.
    if city_code and not city:
        resolved_city = AIRPORT_TO_CITY.get(city_code.upper())
        if resolved_city:
            city = resolved_city
            city_code = None

    params = {}
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
    hotels = _hotel_details(data)

    # If we got a real list back (not an error), apply our own hotel-name,
    # budget, and star filtering, and give a clear message if nothing is
    # left afterwards.
    if isinstance(hotels, list):
        hotels = _apply_local_filters(
            hotels, hotel_budget=hotel_budget, star_rating=star_rating, hotel_name=hotel_name
        )

        if len(hotels) == 0:
            filter_parts = []
            if hotel_name:
                filter_parts.append(f"called \"{hotel_name}\"")
            if hotel_budget:
                filter_parts.append(f"under ${hotel_budget}")
            if star_rating:
                filter_parts.append(f"with {star_rating} stars")
            filter_text = " ".join(filter_parts) if filter_parts else "matching your criteria"
            city_text = f" in {city}" if city else ""

            return {
                "error": True,
                "message": f"I couldn't find any hotels {filter_text}{city_text}. Try a different name, budget, rating, or city.",
            }

    return hotels


@mcp.tool()
def book_hotel(
    hotel_name: str,
    check_in: str,
    check_out: str,
    guest_name: str,
    guest_email: str,
    room_type: str,
):
    """
    Confirms a hotel booking.

    The hotel_name must never be invented by the AI - it must come from a
    previous search_hotel() or list_all_hotels() call.
    """
    if not all([hotel_name, check_in, check_out, guest_name, guest_email, room_type]):
        return {
            "error": True,
            "message": "Missing required booking details.",
        }

    return {
        "confirmationId": f"HTL-{uuid.uuid4().hex[:8].upper()}",
        "status": "confirmed",
        "hotelName": hotel_name,
        "checkInDate": check_in,
        "checkOutDate": check_out,
        "guestName": guest_name,
        "guestEmail": guest_email,
        "roomType": room_type,
    }


if __name__ == "__main__":
    mcp.run("streamable-http")