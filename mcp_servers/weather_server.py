from mcp.server.fastmcp import FastMCP
from typing import Optional
import json
import urllib.request
import urllib.parse
import urllib.error

mcp = FastMCP("Weather Service",port = 8005)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_WEATHER_CODES = {
    0:"Clear sky", 1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
    45:"Fog",48:"Depositing rime fog",
    51:"Light drizzle",53:"Moderate drizzle",55:"Dense drizzle",
    61:"Slight rain",63:"Moderate rain",65:"Heavy rain",
    71:"Slight snow",73:"Moderate snow",75:"Heavy snow",
    80:"Slight rain showers", 81:"Moderate rain showers", 82:"Violent rain showers",
    95:"Thunderstorm",96:"Thunderstorm with slight hail",99:"Thunderstorm with heavy hail",
}

def _get_json(url:str):
    try:
        with urllib.request.urlopen(url,timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8",errors="replace")
        return {"error":True, "status":e.code, "message":body, "url":url}
    except Exception as e:
        return{"error":True,"message":str(e),"url":url}
    
def _geocode_city(city:str):
    params = urllib.parse.urlencode({"name":city,"count":1})
    data = _get_json(f"{GEOCODE_URL}?{params}")
    if isinstance(data,dict) and data.get("error"):
        return None
    results = data.get("results") if isinstance(data,dict) else None
    if not results:
        return None
    top = results[0]
    return {
        "latitude":top.get("latitude"),
        "longtitude":top.get("longitude"),
        "resolved_name":top.get("name"),
        "country":top.get("country"),
        "timezone":top.get("timezone")
    }

@mcp.tool()
def get_weather(city:str,date:Optional[str]=None)->dict:
    """
    Get a weather forecast for a city.
 
    If `date` (YYYY-MM-DD) is given and falls within the next 16 days,
    returns that day's forecast. Otherwise returns a short multi-day
    outlook starting today.
 
    The city is resolved to coordinates automatically - no airport code
    or city_code is needed here (unlike the hotel/flight services).
    """

    if not city:
        return{"error":True,"message":"A city name is required"}
    
    location = _geocode_city(city)

    if not location:
        return {"error":True,"message":f"Could not find a location matching '{city}'."}
    
    params = {
        "latitude":location["latitude"],
        "longitude":location["longitude"],
        "daily":"weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone":"auto",
        "forecast_days":16,
    }

    query_string = urllib.parse.urlencode(params)
    data = _get_json(f"{FORECAST_URL}?{query_string}")

    if isinstance(data,dict) and data.get("error"):
        return data
    
    daily = data.get("daily",{})
    dates = daily.get("time",[])
    codes = daily.get("weathercode",[])
    highs = daily.get("temperature_2m_max",[])
    lows = daily.get("temperature_2m_min",[])
    precip = daily.get("precipitation_sum",[])

    days = []

    for i,d in enumerate(dates):
        days.append({
            "date":d,
            "condition":_WEATHER_CODES.get(codes[i],"Unknown") if i < len(codes) else "Unknown",
            "high_c": highs[i] if i < len(highs) else None,
            "low_c": lows[i] if i < len(lows) else None,
            "precipitation_mm": precip[i] if i < len(precip) else None,
        })
    if date:
        matching = [d for d in days if d["date"] == date]
        if not matching:
            return{
                "error":True,
                "message":f"No forecast available for {date} (only the next 16 days are covered)."
            }
        return{
            "city":location["resolved_name"],
            "country":location["country"],
            "forecast":matching,
        }
    return {
        "city":location["resolved_name"],
        "country":location["country"],
        "forecast":days[:5],
    }

if __name__ == "__main__":
    mcp.run(transport="streamable-http")