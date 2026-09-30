const SITE_URL = "https://www.kanumadhok.com";

export default function TopBar({ view, onViewChange, pinCount }) {
  const tab = (id, label, extra) => (
    <button
      type="button"
      onClick={() => onViewChange(id)}
      aria-current={view === id ? "page" : undefined}
      className={`rounded-md px-3 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-emerald-400 ${
        view === id ? "bg-raised text-white" : "text-zinc-400 hover:text-zinc-200"
      }`}
    >
      {label}
      {extra}
    </button>
  );

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line px-4 md:px-5">
      <p className="flex items-center gap-2 text-sm">
        <a href={SITE_URL} className="text-zinc-400 hover:text-white">Kanu Madhok</a>
        <span className="text-zinc-600" aria-hidden="true">/</span>
        <span className="font-semibold tracking-tight text-white">SQL RAG</span>
      </p>
      <span className="hidden rounded-md border border-line px-2 py-0.5 text-xs text-zinc-400 lg:inline">
        thelook_ecommerce · 7 tables
      </span>
      <span className="hidden rounded-md border border-line px-2 py-0.5 text-xs text-zinc-400 lg:inline">
        gemini-2.5-pro via OpenRouter
      </span>
      <nav className="ml-auto flex items-center gap-1" aria-label="Main">
        {tab("ask", "Ask")}
        {tab(
          "board",
          "Board",
          pinCount > 0 && <span className="ml-1.5 rounded bg-zinc-800 px-1.5 text-xs text-zinc-300">{pinCount}</span>
        )}
        <a
          href="https://www.kanumadhok.com/work/sql-rag"
          target="_blank"
          rel="noreferrer"
          className="ml-2 hidden text-sm text-zinc-400 no-underline hover:text-zinc-200 sm:inline"
        >
          How it works ↗
        </a>
      </nav>
    </header>
  );
}
