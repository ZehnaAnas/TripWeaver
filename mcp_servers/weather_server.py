from mcp.server.fastmcp import FastMCP
from typing import Optional
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import date, datetime, timedelta

mcp = FastMCP("Weather Service", port=8004)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

_WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}

DAILY_FIELDS = "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum"


def _get_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": True, "status": e.code, "message": body, "url": url}
    except Exception as e:
        return {"error": True, "message": str(e), "url": url}


def _geocode_city(city: str):
    params = urllib.parse.urlencode({"name": city, "count": 1})
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
        "country": top.get("country"),
        "timezone": top.get("timezone"),
    }


def _days_to_forecast_from_today(target_date: date) -> int:
    """How many days ahead of today the target date is (negative = in the past)."""
    return (target_date - date.today()).days


@mcp.tool()
def get_weather(city: str, date: Optional[str] = None) -> dict:
    """
    Get weather for a city, for any date - past, present, or future.

    If `date` (YYYY-MM-DD) is within the next 16 days, this returns a real
    forecast. If it's further in the future, or in the past (e.g. checking
    the weather for a past or already-completed flight date), this
    automatically uses real historical weather records instead, going back
    to 1940. Either way, the response looks the same to the caller.

    If `date` is omitted, returns a short forecast starting today.
    """
    if not city:
        return {"error": True, "message": "A city name is required"}

    location = _geocode_city(city)
    if not location:
        return {"error": True, "message": f"Could not find a location matching '{city}'."}

    # No specific date given - just return the normal short-term forecast.
    if not date:
        params = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "daily": DAILY_FIELDS,
            "timezone": "auto",
            "forecast_days": 16,
        }
        query_string = urllib.parse.urlencode(params)
        data = _get_json(f"{FORECAST_URL}?{query_string}")
        if isinstance(data, dict) and data.get("error"):
            return data
        days = _extract_days(data)
        return {
            "city": location["resolved_name"],
            "country": location["country"],
            "forecast": days[:5],
        }

    # A specific date was given - figure out whether it's within the
    # forecast tool's window, or whether we need real historical data.
    try:
        parsed_target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": True, "message": f"'{date}' isn't a valid date - please use YYYY-MM-DD format."}

    days_ahead = _days_to_forecast_from_today(parsed_target_date)

    if 0 <= days_ahead <= 15:
        params = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "daily": DAILY_FIELDS,
            "timezone": "auto",
            "forecast_days": 16,
        }
        query_string = urllib.parse.urlencode(params)
        data = _get_json(f"{FORECAST_URL}?{query_string}")
        if isinstance(data, dict) and data.get("error"):
            return data
        days = _extract_days(data)
        matching = [d for d in days if d["date"] == date]
        if not matching:
            return {"error": True, "message": f"No forecast available for {date}."}
        return {
            "city": location["resolved_name"],
            "country": location["country"],
            "forecast": matching,
        }


    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "start_date": date,
        "end_date": date,
        "daily": DAILY_FIELDS,
        "timezone": "auto",
    }
    query_string = urllib.parse.urlencode(params)
    data = _get_json(f"{ARCHIVE_URL}?{query_string}")

    if isinstance(data, dict) and data.get("error"):
        return data

    days = _extract_days(data)
    if not days:
        return {
            "error": True,
            "message": (
                f"I don't have historical weather data for {date} yet "
                "(very recent dates can take a few days to become available)."
            ),
        }

    return {
        "city": location["resolved_name"],
        "country": location["country"],
        "forecast": days,
        "isHistorical": True,
    }


def _extract_days(data: dict) -> list[dict]:
    """Turns Open-Meteo's daily-arrays response into a list of per-day dicts.
    Shared by both the forecast and archive calls, since they return the
    same shape."""
    daily = data.get("daily", {}) if isinstance(data, dict) else {}
    dates = daily.get("time", [])
    codes = daily.get("weathercode", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])

    days = []
    for i, d in enumerate(dates):
        days.append({
            "date": d,
            "condition": _WEATHER_CODES.get(codes[i], "Unknown") if i < len(codes) else "Unknown",
            "high_c": highs[i] if i < len(highs) else None,
            "low_c": lows[i] if i < len(lows) else None,
            "precipitation_mm": precip[i] if i < len(precip) else None,
        })
    return days


if __name__ == "__main__":
    mcp.run(transport="streamable-http")