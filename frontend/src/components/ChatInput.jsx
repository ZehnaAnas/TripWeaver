import { useState } from "react";

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    setValue("");
    onSend(trimmed);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-panel/95 backdrop-blur-md border border-border-subtle rounded-2xl shadow-2xl px-4 pt-3 pb-2.5"
    >
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Plan a 3-day trip to Paris for next weekend..."
        disabled={disabled}
        autoComplete="off"
        className="w-full bg-transparent outline-none text-[15px] text-ink placeholder:text-muted/70 pb-3"
      />
      <div className="flex items-center justify-between border-t border-border-subtle pt-2.5">
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none">
            <path
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              d="M4 6h16M8 12h12M4 18h16"
            />
          </svg>
          Travel Tools
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Voice input"
            title="Voice input (not yet available)"
            className="w-8 h-8 rounded-full flex items-center justify-center text-muted hover:text-ink transition-colors"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none">
              <path
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm-7-3a7 7 0 0 0 14 0M12 19v3"
              />
            </svg>
          </button>
          <button
            type="submit"
            disabled={disabled}
            aria-label="Send message"
            className="w-9 h-9 rounded-full bg-accent text-canvas flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110 transition-all flex-shrink-0"
          >
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none">
              <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>
      </div>
    </form>
  );
}
