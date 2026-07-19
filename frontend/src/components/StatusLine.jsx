export function StatusLine({ label }) {
  if (!label) return <div className="min-h-[1.4rem]" />;
  return (
    <div className="min-h-[1.4rem] flex items-center gap-2 text-sm text-accent-soft pl-2">
      <span className="flex gap-1">
        <span className="w-1.5 h-1.5 rounded-full bg-accent-soft dot-blink" style={{ animationDelay: "0s" }} />
        <span className="w-1.5 h-1.5 rounded-full bg-accent-soft dot-blink" style={{ animationDelay: "0.2s" }} />
        <span className="w-1.5 h-1.5 rounded-full bg-accent-soft dot-blink" style={{ animationDelay: "0.4s" }} />
      </span>
      {label}
    </div>
  );
}

export function QuickReplies({ hotels, flights, onReply }) {
  const hasHotels = hotels && hotels.length > 0;
  const hasFlights = flights && flights.length > 0;
  if (!hasHotels && !hasFlights) return null;

  const options = [];
  if (hasHotels) options.push("Book the first one");
  if (hasHotels) options.push("Show cheaper options");
  if (hasFlights) options.push("Book the cheapest flight");

  return (
    <div className="flex flex-wrap gap-2 pl-1">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onReply(opt)}
          className="text-xs bg-panel border border-border-subtle rounded-full px-3 py-1.5 text-ink/85 hover:border-accent/50 hover:text-accent-soft transition-colors"
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

export function SavedDetailsSuggestion({ savedMessage, onUse }) {
  if (!savedMessage) return null;
  const preview = savedMessage.length > 60 ? savedMessage.slice(0, 60) + "…" : savedMessage;

  return (
    <div className="pl-1">
      <button
        onClick={() => onUse(savedMessage)}
        className="text-xs bg-panel border border-accent/30 rounded-full px-3 py-1.5 text-accent-soft hover:border-accent/60 transition-colors max-w-full truncate"
        title={savedMessage}
      >
        Use saved details: "{preview}"
      </button>
    </div>
  );
}