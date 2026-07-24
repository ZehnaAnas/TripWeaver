import { useState } from "react";
import Markdown from "./Markdown";

function CopyButton({ text, label = "Copy" }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard API needs a secure context (https/localhost). Fall back
      // to the legacy path so copying still works over plain http.
      const el = document.createElement("textarea");
      el.value = text;
      el.style.position = "fixed";
      el.style.opacity = "0";
      document.body.appendChild(el);
      el.select();
      try {
        document.execCommand("copy");
      } catch {
        return;
      } finally {
        document.body.removeChild(el);
      }
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  return (
    <button
      onClick={handleCopy}
      aria-label={copied ? "Copied" : label}
      className="flex items-center gap-1.5 rounded-md border border-line bg-surface-2 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-muted transition-colors hover:border-accent/50 hover:text-accent"
    >
      {copied ? (
        <svg viewBox="0 0 24 24" width="11" height="11" fill="none" aria-hidden="true">
          <path stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" d="m5 13 4 4L19 7" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" width="11" height="11" fill="none" aria-hidden="true">
          <rect x="9" y="9" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="1.8" />
          <path d="M5 15V6a2 2 0 0 1 2-2h8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      )}
      {copied ? "Copied" : label}
    </button>
  );
}

export default function ChatMessage({ role, text, isError, onRetry, streaming }) {
  const isUser = role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-[15px] leading-relaxed font-medium text-on-accent shadow-sm animate-bubble-in whitespace-pre-wrap break-words">
          {text}
        </div>
      </div>
    );
  }

  // Errors are a different kind of message, not a red version of an answer:
  // they name what failed and offer the way forward.
  if (isError) {
    return (
      <div className="flex justify-start">
        <div className="max-w-[92%] rounded-2xl rounded-bl-md border border-error/40 bg-error/8 px-4 py-3 animate-bubble-in">
          <div className="flex items-center gap-2">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" aria-hidden="true" className="text-error flex-shrink-0">
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
              <path d="M12 7.5v5.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              <circle cx="12" cy="16.3" r="1.05" fill="currentColor" />
            </svg>
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-error">
              Service unavailable
            </span>
          </div>
          <p className="mt-1.5 text-[14px] leading-relaxed text-ink/90">{text}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-2.5 flex items-center gap-1.5 rounded-md border border-error/40 bg-error/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-error transition-colors hover:bg-error/20"
            >
              <svg viewBox="0 0 24 24" width="11" height="11" fill="none" aria-hidden="true">
                <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M20 11.5A8 8 0 1 1 17 5.6M20 4v5h-5" />
              </svg>
              Try again
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="group flex flex-col items-start">
      <div className="max-w-[92%] rounded-2xl rounded-bl-md border border-line bg-surface px-4 py-3 text-[15px] text-ink shadow-sm animate-bubble-in break-words">
        <Markdown>{text}</Markdown>
        {streaming && <span className="caret ml-0.5 text-accent">▮</span>}
      </div>

      {!streaming && text && (
        <div className="mt-1.5 pl-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100 max-md:opacity-100">
          <CopyButton text={text} label="Copy plan" />
        </div>
      )}
    </div>
  );
}
