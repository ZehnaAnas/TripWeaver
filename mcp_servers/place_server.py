import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os

load_dotenv()
mcp = FastMCP("Place Service", port=8003)

OPENTRIPMAP_BASE_URL = "https://api.opentripmap.com/0.1/en/places"
OPENTRIPMAP_API_KEY = os.getenv("OPENTRIPMAP_API_KEY", "")

TAVILY_URL = "https://api.tavily.com/search"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


def _get_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
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


def _geocode_city(city: str):
    params = urllib.parse.urlencode({"name": city, "apikey": OPENTRIPMAP_API_KEY})
    data = _get_json(f"{OPENTRIPMAP_BASE_URL}/geoname?{params}")
    if isinstance(data, dict) and (data.get("error") or "lat" not in data):
        return None
    return {"lat": data.get("lat"), "lon": data.get("lon"), "name": data.get("name")}


@mcp.tool()
def search_places(
    city: str,
    place_type: Optional[str] = None,
    limit: int = 10,
) -> list[dict] | dict:
    """
    Find tourist places to visit in a city.

    `place_type` is an OpenTripMap "kind" and is optional - examples
    include: museums, historic, natural, amusements, foods (restaurants/
    cafes), architecture, religion. If omitted, defaults to general
    interesting_places.

    Returns name, kind/category, and distance (in metres) from the city
    centre for each result. To learn more about a specific place afterwards,
    use get_place_details with that place's name and the city.
    """
    if not OPENTRIPMAP_API_KEY:
        return {
            "error": True,
            "message": (
                "OPENTRIPMAP_API_KEY is not set. Get a free key at "
                "https://opentripmap.io/product and add it to your .env file"
            ),
        }

    if not city:
        return {"error": True, "message": "A city name is required"}

    location = _geocode_city(city)
    if not location:
        return {"error": True, "message": f"Could not find a location matching '{city}'."}

    params = {
        "radius": 10000,
        "lon": location["lon"],
        "lat": location["lat"],
        "kinds": place_type or "interesting_places",
        "limit": limit,
        "format": "json",
        "apikey": OPENTRIPMAP_API_KEY,
    }

    query_string = urllib.parse.urlencode(params)
    data = _get_json(f"{OPENTRIPMAP_BASE_URL}/radius?{query_string}")

    if isinstance(data, dict) and data.get("error"):
        return data
    if not isinstance(data, list):
        return {"error": True, "message": "Unexpected response from place service"}

    return [
        {
            "name": place.get("name") or "Unnamed place",
            "kinds": place.get("kinds"),
            "distance_m": round(place.get("dist", 0)) if place.get("dist") is not None else None,
        }
        for place in data
        if place.get("name")
    ]


@mcp.tool()
def get_place_details(place_name: str, city: str) -> dict:
    """
    Get more information about a specific place, using a web search.

    Unlike search_places, this doesn't need any internal ID - just the
    place's name and the city it's in (both of which you already have from
    a previous search_places result or from what the user typed). Use this
    when the user asks for more detail about a specific place.
    """
    if not TAVILY_API_KEY:
        return {
            "error": True,
            "message": (
                "TAVILY_API_KEY is not set. Get a free key at "
                "https://tavily.com and add it to your .env file"
            ),
        }

    if not place_name:
        return {"error": True, "message": "A place name is required."}

    query = f"{place_name} {city} tourist attraction"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": 3,
        "include_answer": True,
    }

    data = _post_json(TAVILY_URL, payload)

    if isinstance(data, dict) and data.get("error"):
        return data

    # Prefer Tavily's own generated answer (a clean, synthesized summary)
    # if available, falling back to the top result's raw content snippet.
    answer = data.get("answer") if isinstance(data, dict) else None
    results = data.get("results", []) if isinstance(data, dict) else []

    description = answer
    source_url = None
    if not description and results:
        top = results[0]
        description = top.get("content")
        source_url = top.get("url")
    elif results:
        source_url = results[0].get("url")

    if not description:
        return {
            "error": True,
            "message": f"I couldn't find more information about {place_name}.",
        }

    return {
        "name": place_name,
        "description": description,
        "sourceUrl": source_url,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")