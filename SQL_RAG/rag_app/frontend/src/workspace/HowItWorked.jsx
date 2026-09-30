import Pipeline from "./Pipeline.jsx";
import { tablesFromSql } from "./analyzeResult.js";

const SOURCES_SHOWN = 5;

function firstSentence(text) {
  const s = (text || "").trim();
  const end = s.search(/\.\s/);
  return end > 0 ? s.slice(0, end + 1) : s;
}

function Toggle({ label, hint, checked, onChange }) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 py-2">
      <span>
        <span className="block text-sm text-zinc-200">{label}</span>
        <span className="block text-xs text-zinc-500">{hint}</span>
      </span>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="mt-1 size-4 accent-emerald-400" />
    </label>
  );
}

export default function HowItWorked({ turn, settings, onSettingsChange }) {
  const sources = (turn.sources || []).slice(0, SOURCES_SHOWN);
  const set = (key) => (value) => onSettingsChange({ ...settings, [key]: value });

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <Pipeline turn={turn} layout="list" />
        <section className="rounded-xl border border-line bg-panel p-4">
          <h3 className="text-xs font-medium uppercase tracking-wider text-zinc-500">
            Example queries the model saw{turn.sources?.length > SOURCES_SHOWN ? ` · top ${SOURCES_SHOWN} of ${turn.sources.length}` : ""}
          </h3>
          {sources.length === 0 ? (
            <p className="mt-3 text-sm text-zinc-500">{turn.status === "generating" ? "Retrieving…" : "No example queries were returned."}</p>
          ) : (
            <ol className="mt-3 space-y-3">
              {sources.map((s, i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span className="mt-0.5 font-mono text-xs text-emerald-400">#{i + 1}</span>
                  <div className="min-w-0">
                    <p className="text-zinc-200">{firstSentence(s.metadata?.description) || "Example query"}</p>
                    <p className="mt-0.5 truncate font-mono text-[12px] text-zinc-500">{tablesFromSql(s.metadata?.query).join(", ")}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>

      <section className="h-fit rounded-xl border border-line bg-panel p-4">
        <h3 className="text-xs font-medium uppercase tracking-wider text-zinc-500">Retrieval settings</h3>
        <p className="mt-1 text-xs text-zinc-500">Apply to your next question.</p>
        <label className="mt-3 block">
          <span className="flex justify-between text-sm text-zinc-200">Example queries to retrieve <span className="tabular-nums text-zinc-400">{settings.k}</span></span>
          <input type="range" min={5} max={50} step={5} value={settings.k} onChange={(e) => set("k")(Number(e.target.value))} className="mt-2 w-full accent-emerald-400" />
        </label>
        <div className="mt-2 divide-y divide-line">
          <Toggle label="Hybrid search" hint="Vector similarity plus keyword (BM25) matching" checked={settings.hybrid_search} onChange={set("hybrid_search")} />
          <Toggle label="Query rewriting" hint="Rephrase the question before retrieval" checked={settings.query_rewriting} onChange={set("query_rewriting")} />
          <Toggle label="SQL validation" hint="Check tables and columns against the schema" checked={settings.sql_validation} onChange={set("sql_validation")} />
        </div>
      </section>
    </div>
  );
}
