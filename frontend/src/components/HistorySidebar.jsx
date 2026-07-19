export default function HistorySidebar({
  open,
  onClose,
  conversations,
  activeId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
}) {
  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 bg-black/50 z-40 transition-opacity ${
          open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
      />
      <aside
        className={`fixed top-0 left-0 h-full w-80 bg-panel border-r border-border-subtle z-50 flex flex-col p-4 transition-transform duration-300 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display text-lg text-ink">Chat history</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="w-8 h-8 rounded-full bg-panel-alt text-muted hover:text-ink flex items-center justify-center"
          >
            ✕
          </button>
        </div>

        <button
          onClick={onNewChat}
          className="mb-4 rounded-xl border border-accent/40 bg-accent/10 text-accent-soft font-medium py-2.5 hover:bg-accent/15 transition-colors"
        >
          + New chat
        </button>

        <div className="flex-1 overflow-y-auto chat-scroll flex flex-col gap-1">
          {conversations.length === 0 && (
            <p className="text-sm text-muted text-center mt-6">No conversations yet.</p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id ?? c.timestamp}
              className={`group flex items-center gap-1 rounded-lg pr-1 transition-colors ${
                c.id === activeId ? "bg-panel-alt" : "hover:bg-panel-alt/60"
              }`}
            >
              <button
                onClick={() => onSelectConversation(c.id)}
                className={`flex-1 text-left px-3 py-2.5 text-sm truncate ${
                  c.id === activeId ? "text-ink font-medium" : "text-muted"
                }`}
              >
                {c.title || "New chat"}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteConversation(c.id);
                }}
                aria-label="Delete conversation"
                className="opacity-0 group-hover:opacity-100 w-7 h-7 rounded-md flex items-center justify-center text-muted hover:text-error hover:bg-error/10 transition-all flex-shrink-0"
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none">
                  <path
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2m-8 0 1 13a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2l1-13"
                  />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}
