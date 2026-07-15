import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
load_dotenv()
mcp = FastMCP("Activity Service", port=8003)

BASE_URL = "https://api.opentripmap.com/0.1/en/places"

API_KEY =  os.getenv("OPENTRIPMAP_API_KEY","")

def _get_json(url:str):
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8",errors="replace")
        return {"error":True,"status":e.code,"message":body,"url":url}
    except Exception as e:
        return {"error":True,"message":str(e),"url":url}
    
def _geocode_city(city:str):
    params = urllib.parse.urlencode({"name":city,"apikey":API_KEY})
    data = _get_json(f"{BASE_URL}/geoname?{params}")
    if isinstance(data,dict) and (data.get("error") or "lat" not in data):
        return None
    return {"lat":data.get("lat"),"lon":data.get("lon"),"name":data.get("name")}

@mcp.tool()
def search_activities(
    city:str,
    activity_type:Optional[str]=None,
    limit:int = 10,
)-> list[dict] | dict:
    
    """
    Find tourist activities and points of interest in a city.

    `activity_type` is an OpenTripMap "kind" and id optional - examples
    include: museums, historic, natural, amusements, foods (restaurants/
    cafes), architecture, religon. If omitted, defaults to general interesting_places.

    Returns name, kind/category, and approximate distance (in metres)
    from the city centre for each result
    """

    if not API_KEY:
        return{
            "error":True,
            "message":(
                "OPENTRIPMAP_API_KEY is not set. Get a free key at"
                "https://opentripmap.io/product and add it to your .env file"
            ),
        }
    
    if not city:
        return{"error":True,"message":"A city name is required"}
    
    location = _geocode_city(city)
    if not location:
        return {"error":True,"message":f"Could not find a location matching '{city}'."}
    
    params = {
        "radius" : 10000,
        "lon": location["lon"],
        "lat" : location["lat"],
        "kinds" : activity_type or "interesting_places",
        "limit" : limit,
        "format":json,
        "apikey":API_KEY,
    }

    query_string = urllib.parse.urlencode(params)
    data = _get_json(f"{BASE_URL}/radius?{query_string}")

    if isinstance(data,dict) and data.get("error"):
        return data
    if not isinstance(data,list):
        return {"error":True,"message":"Unexpected response from activities service"}
    
    return [
        {
            "name":place.get("name") or "Unnamed place",
            "kinds":place.get("kinds"),
            "distance_m":round(place.get("dist",0)) if place.get("dist") is not None else None,
            "xid":place.get("xid"),
        }
        for place in data
        if place.get("name")
    ]
    

if __name__ == "__main__":
    mcp.run(transport="streamable-http")