import Logo from "./Logo";

function IconButton({ onClick, label, children, tone = "default", disabled }) {
  const tones = {
    default: "text-muted hover:text-ink hover:border-accent/50",
    danger: "text-muted hover:text-error hover:border-error/50",
  };
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={label}
      disabled={disabled}
      className={`flex h-9 w-9 items-center justify-center rounded-full border border-line bg-surface transition-colors disabled:opacity-35 disabled:hover:border-line disabled:hover:text-muted ${tones[tone]}`}
    >
      {children}
    </button>
  );
}

export default function Navbar({
  onToggleHistory,
  onNewChat,
  onDeleteChat,
  canDelete,
  theme,
  onToggleTheme,
}) {
  const isDark = theme === "dark";

  return (
    <header className="relative z-30 flex items-center justify-between border-b border-line/70 px-4 py-3 md:px-6">
      <Logo />

      <div className="flex items-center gap-2">
        <IconButton onClick={onNewChat} label="New chat">
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none" aria-hidden="true">
            <path stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" d="M12 5v14M5 12h14" />
          </svg>
        </IconButton>

        <IconButton onClick={onToggleHistory} label="Chat history">
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none" aria-hidden="true">
            <path stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" d="M21 11.5a8.5 8.5 0 1 1-3.5-6.86M21 4v5h-5M12 8v4.5l3 1.8" />
          </svg>
        </IconButton>

        <IconButton
          onClick={onToggleTheme}
          label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        >
          {isDark ? (
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.7" />
              <path stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4M18.8 5.2l-1.4 1.4M6.6 17.4l-1.4 1.4" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" aria-hidden="true">
              <path stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" d="M20 14.2A8.2 8.2 0 0 1 9.8 4a8.4 8.4 0 1 0 10.2 10.2Z" />
            </svg>
          )}
        </IconButton>

        <IconButton
          onClick={onDeleteChat}
          label="Delete this chat"
          tone="danger"
          disabled={!canDelete}
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true">
            <path stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2m-8 0 1 13a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2l1-13" />
          </svg>
        </IconButton>
      </div>
    </header>
  );
}
