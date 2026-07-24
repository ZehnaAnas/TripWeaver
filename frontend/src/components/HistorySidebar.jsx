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
        aria-hidden="true"
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity ${
          open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      <aside
        aria-hidden={!open}
        inert={!open ? true : undefined}
        className={`fixed left-0 top-0 z-50 flex h-full w-[min(20rem,85vw)] flex-col border-r border-line bg-surface p-4 transition-transform duration-300 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted">
            Chat history
          </h2>
          <button
            onClick={onClose}
            aria-label="Close history"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-2 text-muted transition-colors hover:text-ink"
          >
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" aria-hidden="true">
              <path stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <button
          onClick={onNewChat}
          className="mb-4 rounded-xl border border-accent/40 bg-accent/10 py-2.5 text-[13.5px] font-medium text-accent transition-colors hover:bg-accent/15"
        >
          + New chat
        </button>

        <div className="chat-scroll flex flex-1 flex-col gap-0.5 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="mt-8 px-2 text-center">
              <p className="text-[13.5px] text-ink/80">No trips planned yet</p>
              <p className="mt-1 text-[12.5px] leading-relaxed text-muted">
                Ask about a hotel, a flight or a city and it will show up here.
              </p>
            </div>
          ) : (
            conversations.map((c) => (
              <div
                key={c.key}
                className={`group flex items-center gap-1 rounded-lg pr-1 transition-colors ${
                  c.key === activeId ? "bg-surface-2" : "hover:bg-surface-2/60"
                }`}
              >
                <button
                  onClick={() => onSelectConversation(c.key)}
                  className={`flex-1 truncate px-3 py-2.5 text-left text-[13.5px] ${
                    c.key === activeId ? "font-medium text-ink" : "text-muted"
                  }`}
                >
                  {c.title || "New chat"}
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(c.key);
                  }}
                  aria-label={`Delete conversation: ${c.title || "New chat"}`}
                  className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md text-muted opacity-0 transition-all hover:bg-error/10 hover:text-error focus-visible:opacity-100 group-hover:opacity-100 max-md:opacity-100"
                >
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" aria-hidden="true">
                    <path stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2m-8 0 1 13a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2l1-13" />
                  </svg>
                </button>
              </div>
            ))
          )}
        </div>
      </aside>
    </>
  );
}