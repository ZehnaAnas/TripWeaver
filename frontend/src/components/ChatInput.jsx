import { useEffect, useRef, useState } from "react";

export default function ChatInput({ onSend, onStop, busy }) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  // Grow with the content up to a ceiling, then scroll - so a long,
  // detailed trip brief stays visible while typing on desktop and mobile.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || busy) return;
    setValue("");
    onSend(trimmed);
  };

  const handleKeyDown = (e) => {
    // Enter sends, Shift+Enter starts a new line.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="rounded-2xl border border-line bg-surface/95 px-3.5 pt-3 pb-2.5 shadow-lg backdrop-blur-md transition-colors focus-within:border-accent/50">
      <label htmlFor="chat-input" className="sr-only">
        Message TripWeaver
      </label>
      <textarea
        id="chat-input"
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Plan three days in Paris - hotel near the centre, flights from Colombo"
        autoComplete="off"
        className="chat-scroll w-full resize-none bg-transparent pb-2.5 text-[15px] leading-relaxed text-ink outline-none placeholder:text-muted/70"
      />

      <div className="flex items-center justify-between gap-3 border-t border-line pt-2.5">
        <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted/80">
          <span className="hidden sm:inline">Enter to send · Shift+Enter for a new line</span>
          <span className="sm:hidden">Hotels · Flights · Activities</span>
        </span>

        {busy ? (
          <button
            type="button"
            onClick={onStop}
            aria-label="Stop generating"
            className="flex h-9 items-center gap-1.5 rounded-full border border-line bg-surface-2 px-3 font-mono text-[10px] uppercase tracking-[0.14em] text-muted transition-colors hover:border-error/50 hover:text-error"
          >
            <span className="block h-2.5 w-2.5 rounded-[2px] bg-current" />
            Stop
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!value.trim()}
            aria-label="Send message"
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-accent text-on-accent transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-35"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true">
              <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
