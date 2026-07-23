import { WeaveMark } from "./Logo";

/* Grouped by which specialist agent handles them, so the empty state
   doubles as a map of what the system can actually do. */
const STARTERS = [
  { agent: "Hotels", query: "Find hotels in Bangkok under $120 a night" },
  { agent: "Flights", query: "Show me flights from Colombo to Seoul next month" },
  { agent: "Things to do", query: "What's worth seeing in Tokyo over three days?" },
  { agent: "Travel Q&A", query: "Do I need a visa to visit Thailand?" },
];

export default function Hero({ onSuggestionClick, disabled }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-2 py-8 text-center">
      <WeaveMark size={34} className="text-accent animate-rise-in" />

      <h1
        className="mt-5 font-display text-[34px] leading-[1.05] tracking-[-0.04em] text-ink md:text-[46px] animate-rise-in"
        style={{ animationDelay: "60ms" }}
      >
        Where are we
        <br />
        <span className="text-accent">weaving</span> a trip to?
      </h1>

      <p
        className="mt-4 max-w-sm text-[14.5px] leading-relaxed text-muted animate-rise-in"
        style={{ animationDelay: "120ms" }}
      >
        Ask in plain language. Specialist agents handle hotels, flights and things
        to do, and hand the answer back as one plan.
      </p>

      <div className="mt-8 grid w-full max-w-xl gap-2 sm:grid-cols-2">
        {STARTERS.map((s, i) => (
          <button
            key={s.agent}
            onClick={() => onSuggestionClick(s.query)}
            disabled={disabled}
            style={{ animationDelay: `${180 + i * 60}ms` }}
            className="group animate-rise-in rounded-xl border border-line bg-surface p-3.5 text-left transition-colors hover:border-accent/60 disabled:opacity-40"
          >
            <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-muted group-hover:text-accent">
              {s.agent}
            </span>
            <span className="mt-1.5 block text-[13.5px] leading-snug text-ink/90">
              {s.query}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
