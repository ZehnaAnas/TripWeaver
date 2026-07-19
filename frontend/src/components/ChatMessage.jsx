import { useState } from "react";

export default function ChatMessage({ role, text, isError, onRetry }) {
  const [copied, setCopied] = useState(false);
  const isConfirmation = text.includes("Confirmation ID");
  const isUser = role === "user";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard access can fail silently - not a critical action
    }
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[78%] px-4 py-2.5 rounded-2xl text-[15px] leading-relaxed whitespace-pre-wrap shadow-lg animate-bubble-in backdrop-blur-sm ${
          isUser
            ? "bg-accent text-canvas rounded-br-md font-medium"
            : isError
            ? "bg-panel/95 border border-error/50 text-error rounded-bl-md"
            : "bg-panel/95 border border-border-subtle text-ink rounded-bl-md"
        }`}
      >
        {text}

        {isConfirmation && !isUser && (
          <button
            onClick={handleCopy}
            className="block mt-2 text-xs bg-panel-alt border border-border-subtle rounded-md px-2.5 py-1 text-accent-soft hover:border-accent/50"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        )}

        {isError && onRetry && (
          <button
            onClick={onRetry}
            className="block mt-2 text-xs bg-error/10 border border-error/40 rounded-md px-2.5 py-1 text-error hover:bg-error/20"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
