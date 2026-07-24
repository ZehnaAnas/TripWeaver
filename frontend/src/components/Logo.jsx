/**
 * The wordmark. "TripWeaver" is a weaving metaphor, so the mark is two
 * threads crossing over an under - drawn as one continuous stroke - and
 * the wordmark splits weight rather than colour so it stays legible at
 * small sizes and in both themes.
 */
export function WeaveMark({ size = 26, className = "" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={className}
      aria-hidden="true"
      fill="none"
    >
      {/* outbound thread */}
      <path
        d="M2 18C6 18 6 6 10 6s4 12 8 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.45"
      />
      {/* return thread, woven the other way */}
      <path
        d="M22 6c-4 0-4 12-8 12S10 6 6 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function Logo() {
  return (
    <div className="flex items-center gap-2.5 select-none">
      <WeaveMark className="text-accent" />
      <div className="flex items-baseline gap-2">
        <span className="font-display text-[21px] leading-none tracking-[-0.035em] text-ink">
          <span className="font-extrabold">Trip</span>
          <span className="font-normal">weaver</span>
        </span>
        <span className="hidden sm:inline font-mono text-[9px] uppercase tracking-[0.22em] text-muted">
          multi-agent
        </span>
      </div>
    </div>
  );
}
