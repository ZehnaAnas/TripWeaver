from mcp.server.fastmcp import FastMCP
from typing import Optional
import json
import urllib.request
import urllib.parse
import urllib.error

mcp = FastMCP("Transport Service",port=8004)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
OSRM_URL = "https://router.project-osrm.org"


_VALID_MODES = {"driving":"driving","walking":"foot","cycling":"bike"}

def _get_json(url:str):
    try:
        with urllib.request.urlopen(url,timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8",errors="replace")
        return {"error":True,"status":e.code,"message":body,"url":url}
    except Exception as e:
        return {"error":True,"message":str(e),"url":url}
    
def _geocode(place:str):
    params = urllib.parse.urlencode({"name": place, "count": 1})
    data = _get_json(f"{GEOCODE_URL}?{params}")
    if isinstance(data, dict) and data.get("error"):
        return None
    results = data.get("results") if isinstance(data, dict) else None
    if not results:
        return None
    top = results[0]
    return {
        "latitude": top.get("latitude"),
        "longitude": top.get("longitude"),
        "resolved_name": top.get("name"),
    }

@mcp.tool()
def get_directions(
    origin:str,
    destination:str,
    mode:Optional[str]="driving"
)-> dict:
    """
    Get local transport directions between two named places (e.g. a
    hotel and an attraction, or two neighbourhoods in the same city).
 
    `mode` must be one of: driving, walking, cycling. Defaults to driving.
 
    Both `origin` and `destination` are resolved to coordinates
    automatically - no lat/lon is needed from the caller. Distance is
    returned in kilometres and duration in minutes.
 
    This is for short local trips (e.g. getting around a city), not for
    intercity flights - use the flight service for that.
    """
    if not origin or not destination:
        return {"error":True,"message":"Both an origin and a destination are required"}
    
    profile = _VALID_MODES.get((mode or "driving").lower())
    if not profile:
        return{
            "error":True,
            "message":f"Unsupported mode '{mode}'. Use driving, walking, or cycling",
        }
    origin_loc = _geocode(origin)
    if not origin_loc:
        return {"error":True,"message":f"Could not find a location matching '{origin}'."}
    dest_loc = _geocode(destination)
    if not dest_loc:
        return {"error":True,"message":f"Could not find a location matching '{destination}'."}
    
    coords = (
        f"{origin_loc['longitude']},{origin_loc['latitude']};"
        f"{dest_loc['longitude']},{dest_loc['latitude']}"
    )

    url = f"{OSRM_URL}/route/v1/{profile}/{coords}?overview=false"
    data = _get_json(url)

    if isinstance(data,dict) and data.get("error"):
        return data
    
    routes = data.get("routes") if isinstance(data,dict) else None
    if not routes:
        return{
            "error":True,
            "message":f"No {mode} route found between {origin} and {destination}."
        }
    
    route = routes[0]

    return {
        "origin":origin_loc["resolved_name"],
        "destination":dest_loc["resolved_name"],
        "mode":mode,
        "distance_km":round(route["distance"]/1000,1),
        "duration_minutes":round(route["duration"]/60),
    }

if __name__ == "__main__":
    mcp.run(transport="streamable-http")