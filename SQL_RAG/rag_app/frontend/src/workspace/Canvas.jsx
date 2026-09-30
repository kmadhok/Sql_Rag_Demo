import { useEffect, useState } from "react";
import HowItWorked from "./HowItWorked.jsx";
import Pipeline from "./Pipeline.jsx";
import ResultView from "./ResultView.jsx";
import SqlBlock from "./SqlBlock.jsx";

const TABS = [
  { id: "result", label: "Result" },
  { id: "sql", label: "SQL" },
  { id: "how", label: "How it worked" },
];

function Skeleton() {
  return (
    <div className="space-y-3" aria-hidden="true">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => <div key={i} className="h-[88px] animate-pulse rounded-xl border border-line bg-panel" />)}
      </div>
      <div className="h-64 animate-pulse rounded-xl border border-line bg-panel" />
    </div>
  );
}

function errorTitle(turn) {
  if (/can't reach the api/i.test(turn.error || "")) return "Couldn't reach the service";
  return turn.failedStep === "execute" ? "The query didn't run" : "Couldn't write a query for that";
}

function ErrorCard({ turn, onRetry, onShowSql }) {
  return (
    <div role="alert" className="rounded-xl border border-rose-400/30 bg-rose-400/5 p-5">
      <p className="font-medium text-rose-200">{errorTitle(turn)}</p>
      <p className="mt-1 text-sm text-zinc-300">{turn.error}</p>
      <div className="mt-4 flex gap-2">
        <button type="button" onClick={onRetry} className="rounded-md bg-zinc-100 px-3 py-1.5 text-sm font-medium text-zinc-900">Try again</button>
        {turn.sql && <button type="button" onClick={onShowSql} className="rounded-md border border-line px-3 py-1.5 text-sm text-zinc-200">View the SQL</button>}
      </div>
    </div>
  );
}

export default function Canvas({ turn, pinned, onPin, onRetry, settings, onSettingsChange }) {
  const [tab, setTab] = useState("result");
  const [copied, setCopied] = useState(false);
  useEffect(() => setTab("result"), [turn.id]);

  const running = turn.status === "generating" || turn.status === "executing";
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(turn.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1180px] p-4 md:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
        <h2 className="min-w-0 text-xl font-semibold tracking-tight text-white sm:flex-1">{turn.question}</h2>
        <div className="flex gap-2 text-sm">
          <button type="button" onClick={copy} disabled={!turn.sql} className="rounded-md border border-line px-3 py-1.5 text-zinc-200 hover:bg-panel disabled:opacity-40">
            {copied ? "Copied" : "Copy SQL"}
          </button>
          <button
            type="button"
            onClick={onPin}
            disabled={turn.status !== "done" || pinned}
            className="rounded-md bg-emerald-400 px-3 py-1.5 font-medium text-zinc-950 disabled:opacity-40"
          >
            {pinned ? "Pinned ✓" : "Pin to board"}
          </button>
        </div>
      </div>

      <div role="tablist" aria-label="Answer views" className="mt-4 flex gap-5 border-b border-line text-sm">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            type="button"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`-mb-px border-b-2 pb-2 transition-colors ${tab === t.id ? "border-emerald-400 text-white" : "border-transparent text-zinc-500 hover:text-zinc-300"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-5" role="tabpanel">
        {tab === "result" && (
          <div className="space-y-3">
            {running && <Skeleton />}
            {turn.status === "error" && <ErrorCard turn={turn} onRetry={() => onRetry(turn.question)} onShowSql={() => setTab("sql")} />}
            {turn.status === "done" && <ResultView turn={turn} />}
            <Pipeline turn={turn} />
          </div>
        )}
        {tab === "sql" && (turn.sql ? <SqlBlock sql={turn.sql} /> : <p className="text-sm text-zinc-500">{running ? "Writing SQL…" : "No SQL was produced."}</p>)}
        {tab === "how" && <HowItWorked turn={turn} settings={settings} onSettingsChange={onSettingsChange} />}
      </div>
    </div>
  );
}
