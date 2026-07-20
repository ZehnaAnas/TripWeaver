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


@mcp.tool()
def search_places(
    city: str,
    place_type: Optional[str] = None,
    limit: int = 10,
) -> list[dict] | dict:
    """
    Find tourist places to visit in a city, using a Tavily web search.

    `place_type` is free text and optional - e.g. "museums", "nightlife",
    "family-friendly parks", "hidden gem cafes". If omitted, searches
    generally for top tourist attractions.

    Each result is a real web page about a place (its title, a short
    description, and a source URL) rather than a single geocoded point -
    treat the title as the place's name. To learn more about a specific
    result afterwards, use get_place_details with that place's name and
    the city.
    """
    if not TAVILY_API_KEY:
        return {
            "error": True,
            "message": (
                "TAVILY_API_KEY is not set. Get a free key at "
                "https://tavily.com and add it to your .env file"
            ),
        }

    if not city:
        return {"error": True, "message": "A city name is required"}

    query = f"best {place_type or 'tourist attractions'} to visit in {city}"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": limit,
        "include_answer": False,
    }

    data = _post_json(TAVILY_URL, payload)

    if isinstance(data, dict) and data.get("error"):
        return data

    results = data.get("results", []) if isinstance(data, dict) else []
    if not results:
        return {"error": True, "message": f"I couldn't find places to visit in '{city}'."}

    return [
        {
            "name": r.get("title"),
            "description": r.get("content"),
            "sourceUrl": r.get("url"),
        }
        for r in results
        if r.get("title")
    ]


@mcp.tool()
def get_place_details(place_name: str, city: str) -> dict:
    """
    Get more information about a specific place, using a Tavily web search.

    Just needs the place's name and the city it's in (both of which you
    already have from a previous search_places result or from what the
    user typed). Use this when the user asks for more detail about a
    specific place.
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