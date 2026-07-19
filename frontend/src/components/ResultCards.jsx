export function HotelCards({ hotels }) {
  if (!hotels || hotels.length === 0) return null;
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-3 my-1">
      {hotels.slice(0, 5).map((hotel, i) => (
        <div
          key={i}
          className="bg-panel border border-border-subtle rounded-xl p-4 animate-bubble-in"
        >
          <div className="font-medium text-ink text-sm">{hotel.hotelName || "Hotel"}</div>
          <div className="text-xs text-muted mb-2">{hotel.city || ""}</div>
          <div className="text-xs text-ink/80 mt-1">{hotel.starRating ?? "N/A"}-star rating</div>
          <div className="text-xs text-ink/80 mt-1">
            USD {hotel.pricePerNight ?? "N/A"} / night
          </div>
          <div className="text-xs text-muted mt-1">
            {hotel.availableRooms ?? "N/A"} rooms available
          </div>
        </div>
      ))}
    </div>
  );
}

export function FlightCards({ flights }) {
  if (!flights || flights.length === 0) return null;
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-3 my-1">
      {flights.slice(0, 5).map((flight, i) => {
        const origin = flight.originAirport || flight.originCity || "?";
        const destination = flight.destinationAirport || flight.destinationCity || "?";
        return (
          <div
            key={i}
            className="bg-panel border border-border-subtle rounded-xl p-4 animate-bubble-in"
          >
            <div className="font-medium text-ink text-sm">{flight.airline || "Flight"}</div>
            <div className="text-xs text-muted mb-2">
              {origin} → {destination}
            </div>
            <div className="text-xs text-ink/80 mt-1">{flight.flightDate || "N/A"}</div>
            <div className="text-xs text-ink/80 mt-1">
              {flight.departureTime || "N/A"} – {flight.arrivalTime || "N/A"}
            </div>
            <div className="text-xs text-muted mt-1">
              USD {flight.price ?? "N/A"} · {flight.availableSeats ?? "N/A"} seats
            </div>
          </div>
        );
      })}
    </div>
  );
}
