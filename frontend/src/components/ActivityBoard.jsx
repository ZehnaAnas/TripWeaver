/**
 * Agent-activity visualisation.
 *
 * The spec defines a fixed activity lifecycle (ROUTING / SEARCHING /
 * BOOKING / RESPONDING / CLARIFYING), so the UI surfaces it literally:
 * an airport-style status board. The status code is the machine-readable
 * value the backend streams on each `status` event; the line under it is
 * the human sentence. Every step of the turn stays on screen as a small
 * tick, so the traveller can see the whole route the request took -
 * router first, then the specialist agent, then the finalizer.
 */

const AGENT_BY_NODE = {
  router: "Router",
  hotel_node: "Hotel agent",
  flight_node: "Flight agent",
  activity_node: "Activity agent",
  unknown_node: "Travel Q&A",
  finalize_answer: "Finalizer",
};

// Falls back gracefully if the backend ever emits a status we don't know.
const STATUS_TONE = {
  CONNECTING: "text-muted",
  ROUTING: "text-muted",
  SEARCHING: "text-board",
  BOOKING: "text-board",
  RESPONDING: "text-accent",
  CLARIFYING: "text-accent",
};

function agentName(node) {
  return AGENT_BY_NODE[node] || "Agent";
}

export default function ActivityBoard({ steps, busy, streaming }) {
  if (!busy && !streaming) return <div className="h-2" />;

  const current = steps[steps.length - 1];
  const done = steps.slice(0, -1);

  // Once tokens start arriving the board reports RESPONDING regardless of
  // which node last checked in - that is what the traveller is watching.
  const statusCode = streaming ? "RESPONDING" : current?.status || "CONNECTING";
  const label = streaming
    ? "Writing your answer"
    : current?.label || "Reaching the travel assistant";
  const who = streaming ? "Finalizer" : current ? agentName(current.node) : "TripWeaver";
  const tone = STATUS_TONE[statusCode] || "text-accent";

  return (
    <div
      role="status"
      aria-live="polite"
      className="mb-2.5 rounded-xl border border-line bg-surface/80 backdrop-blur-sm px-3.5 py-2.5 animate-fade-in"
    >
      <div className="flex items-center gap-2.5">
        <span className="relative flex h-2 w-2 flex-shrink-0">
          <span className={`absolute inline-flex h-full w-full rounded-full bg-current opacity-60 ${tone} dot-blink`} />
          <span className={`relative inline-flex h-2 w-2 rounded-full bg-current ${tone}`} />
        </span>

        <span
          key={statusCode}
          className={`font-mono text-[10px] font-medium uppercase tracking-[0.2em] ${tone} animate-board-flip`}
        >
          {statusCode}
        </span>

        <span className="text-[11px] text-muted truncate">{who}</span>
      </div>

      <p key={label} className="mt-1 text-[13px] text-ink/85 animate-board-flip">
        {label}
        <span className="caret ml-0.5 text-accent">▮</span>
      </p>

      {done.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line pt-2">
          {done.map((s) => (
            <span
              key={s.id}
              className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted/80"
            >
              <span className="text-accent">✓</span> {s.status}
              <span className="text-muted/50"> · {agentName(s.node)}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
