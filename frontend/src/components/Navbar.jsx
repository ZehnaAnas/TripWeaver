import { useState, useRef, useEffect } from "react";

function IconButton({ onClick, label, children, danger }) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={label}
      className={`w-10 h-10 rounded-full flex items-center justify-center border transition-colors ${
        danger
          ? "border-border-subtle bg-panel text-muted hover:text-error hover:border-error/50"
          : "border-border-subtle bg-panel text-muted hover:text-ink hover:border-accent/50"
      }`}
    >
      {children}
    </button>
  );
}

export default function Navbar({ onToggleHistory, onDeleteChat, canDelete }) {
  const [profileOpen, setProfileOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="flex items-center justify-between px-6 py-4 relative z-30">
      <div className="flex items-center gap-2">
        <span className="font-display text-lg tracking-wide text-ink">TripWeaver</span>
        <span className="text-[10px] uppercase tracking-widest bg-accent/15 text-accent-soft border border-accent/30 rounded-full px-2 py-0.5">
          AI
        </span>
      </div>

      <div className="flex items-center gap-2.5">
        <IconButton onClick={onDeleteChat} label="Delete this chat" danger={canDelete}>
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none">
            <path
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2m-8 0 1 13a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2l1-13"
            />
          </svg>
        </IconButton>

        <IconButton onClick={onToggleHistory} label="Chat history">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
            <path
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 11.5a8.5 8.5 0 1 1-3.5-6.86M21 4v5h-5"
            />
          </svg>
        </IconButton>

        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setProfileOpen((v) => !v)}
            aria-label="Profile"
            className="w-10 h-10 rounded-full bg-gradient-to-br from-accent to-accent-soft text-canvas font-semibold text-sm flex items-center justify-center"
          >
            G
          </button>

          {profileOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-panel border border-border-subtle rounded-xl shadow-xl overflow-hidden animate-fade-in">
              <button className="w-full text-left px-4 py-3 text-sm text-ink hover:bg-panel-alt transition-colors">
                Sign in
              </button>
              <button className="w-full text-left px-4 py-3 text-sm text-muted hover:bg-panel-alt transition-colors border-t border-border-subtle">
                Settings
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
