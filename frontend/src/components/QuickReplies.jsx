/**
 * Quick replies for the most recent answer.
 *
 * The backend's `done` event tells us whether the turn produced hotel or
 * flight results; we keep only that one-word signal on the message (never
 * the result objects themselves) and use it to offer the follow-ups a
 * traveller actually types next.
 */
const REPLIES_BY_KIND = {
  hotel: ["Book the first one", "Show cheaper options", "Anything closer to the centre?"],
  flight: ["Book the cheapest flight", "Show earlier departures", "Any direct flights?"],
  activity: ["What else is nearby?", "Find hotels there", "How do I get around?"],
  default: ["Find hotels there", "Check flights", "What can I do there?"],
};

export default function QuickReplies({ resultKind, onReply, disabled }) {
  const options = REPLIES_BY_KIND[resultKind] || REPLIES_BY_KIND.default;

  return (
    <div className="flex flex-wrap gap-2 pl-1 pt-1">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onReply(opt)}
          disabled={disabled}
          className="rounded-full border border-line bg-surface px-3 py-1.5 text-[12.5px] text-ink/85 transition-colors hover:border-accent/60 hover:text-accent disabled:opacity-40"
        >
          {opt}
        </button>
      ))}
    </div>
  );
}
