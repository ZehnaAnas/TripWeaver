const SUGGESTIONS = [
  { label: "Hotels in Bangkok", query: "Find hotels in Bangkok" },
  { label: "Flights to Seoul", query: "Find flights to Seoul" },
  { label: "Weather in Busan", query: "What's the weather in Busan?" },
  { label: "Places to visit in Tokyo", query: "What are some places to visit in Tokyo?" },
];

export default function Hero({ onSuggestionClick }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center gap-6 px-6 animate-fade-in">
      <h1 className="font-display text-4xl md:text-5xl text-ink font-medium">
        Where would you like to go?
      </h1>
      <p className="text-muted max-w-md text-[15px] leading-relaxed">
        Search hotels, book flights, discover places to visit, and check weather
        forecasts with TripWeaver AI.
      </p>

      <div className="flex flex-wrap justify-center gap-2.5 max-w-lg">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.label}
            onClick={() => onSuggestionClick(s.query)}
            className="text-sm bg-panel border border-border-subtle rounded-full px-4 py-2 text-ink/90 hover:border-accent/50 hover:text-accent-soft transition-colors"
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}
