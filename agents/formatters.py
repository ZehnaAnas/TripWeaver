def _format_hotel(hotel: dict) -> str:
    name = hotel.get("hotelName", "Unknown hotel")

    city_data = hotel.get("city", "unknown city")
    if isinstance(city_data, dict):
        city = city_data.get("name", "unknown city")
    else:
        city = city_data

    stars = hotel.get("starRating", "N/A")
    price = hotel.get("price", hotel.get("pricePerNight", "N/A"))
    currency = hotel.get("currency", "USD")

    available = hotel.get(
        "available_rooms",
        hotel.get("availableRooms", hotel.get("available", "N/A"))
    )

    return (
        f"{name} in {city}, "
        f"{stars} stars - {currency} {price}/night - "
        f"{available} rooms"
    )


def _format_hotel_detailed(index: int, hotel: dict) -> str:
    """Richer, bulleted format used for search results (not list_all)."""
    name = hotel.get("hotelName", "Unknown hotel")
    address = hotel.get("address", "Address not available")
    stars = hotel.get("starRating", "N/A")
    price = hotel.get("price", hotel.get("pricePerNight", "N/A"))
    currency = hotel.get("currency", "USD")
    available = hotel.get(
        "available_rooms",
        hotel.get("availableRooms", hotel.get("available", "N/A"))
    )
    amenities = hotel.get("amenities")
    amenities_line = ", ".join(amenities) if isinstance(amenities, list) and amenities else "N/A"

    return (
        f"{index}. {name}\n"
        f"   - Location: {address}\n"
        f"   - Price: {currency} {price} per night\n"
        f"   - Rating: {stars} stars\n"
        f"   - Availability: {available} rooms available\n"
        f"   - Amenities: {amenities_line}"
    )


def _format_flight(flight: dict) -> str:
    airline = flight.get(
        "airline", 
        "Unknown airline"
        )
    
    origin = flight.get(
        "originAirport") or flight.get(
            "originCity",
            "unknown"
            )
    
    destination  = flight.get(
        "destinationAirport") or flight.get(
            "destinationCity",
            "unknown"
            )
    
    flight_date = flight.get(
        "flightDate",
        "unknown"
        )
    
    departure_time = flight.get(
        "departureTime",
        "N/A"
        )
    
    arrival_time = flight.get(
        "arrivalTime",
        "N/A"
        )
    
    price = flight.get(
        "price",
        "N/A"
        )
    
    currency = flight.get(
        "currency",
        "USD"
        )
    
    seats = flight.get(
        "availableSeats",
        "N/A"
        )
    
    number = flight.get(
        "flightNumber",
        flight.get("flight_number", flight.get("flightNo", "N/A"))
    )

    return (
        f"{airline} {number} from {origin} to {destination} "
        f"on {flight_date}, {departure_time} - {arrival_time} "
        f"- {currency} {price} - {seats} seats"
    )


def _format_flight_detailed(index: int, flight: dict) -> str:
    """Richer, bulleted format used for search results (not list_all)."""
    airline = flight.get("airline", "Unknown airline")
    origin = flight.get("originAirport") or flight.get("originCity", "unknown")
    destination = flight.get("destinationAirport") or flight.get("destinationCity", "unknown")
    flight_date = flight.get("flightDate", "unknown")
    departure_time = flight.get("departureTime", "N/A")
    arrival_time = flight.get("arrivalTime", "N/A")
    price = flight.get("price", "N/A")
    currency = flight.get("currency", "USD")
    seats = flight.get("availableSeats", "N/A")
    number = flight.get("flightNumber", flight.get("flight_number", flight.get("flightNo", "N/A")))

    return (
        f"{index}. {airline} {number}\n"
        f"   - Route: {origin} to {destination}\n"
        f"   - Date: {flight_date}\n"
        f"   - Time: {departure_time} - {arrival_time}\n"
        f"   - Price: {currency} {price}\n"
        f"   - Availability: {seats} seats"
    )

def _format_weather_day(day:dict)->str:
    date = day.get("date","unknown date")
    condition = day.get("condition","N/A")
    high = day.get("high_c","N/A")
    low = day.get("low_c","N/A")
    return f"{date}:{condition},{low}-{high}\u00b0C"

def _format_activity(place:dict)->str:
    name = place.get("name","Unknown place")
    category = place.get("category","attraction")
    return f"{name} ({category})"
