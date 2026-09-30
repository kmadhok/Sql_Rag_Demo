import { useEffect, useState } from "react";
import { formatBytes, formatSeconds, tablesFromSql } from "./analyzeResult.js";
import { GENERATION_MODEL } from "./askFlow.js";

function useElapsed(startedAt, running) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!running) return undefined;
    const timer = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(timer);
  }, [running]);
  return (now - startedAt) / 1000;
}

function stepStates(turn) {
  const { status, failedStep, usage } = turn;
  if (status === "generating") return ["active", "active", "active", "pending", "pending"];
  if (status === "executing") return ["done", "done", "done", "done", "active"];
  if (status === "done") return ["done", "done", "done", "done", "done"];
  if (failedStep === "execute") return ["done", "done", "done", "done", "failed"];
  return usage ? ["done", "done", "failed", "pending", "pending"] : ["pending", "pending", "failed", "pending", "pending"];
}

export function pipelineSteps(turn) {
  const usage = turn.usage || {};
  const tables = tablesFromSql(turn.sql);
  const validation = usage.sql_validation;
  const exec = turn.execution;
  return [
    {
      name: "Retrieve",
      time: usage.retrieval_time,
      detail: turn.sources ? `${turn.sources.length} similar example queries` : "Similar example queries",
    },
    {
      name: "Schema",
      detail: tables.length ? tables.join(", ") : "Relevant tables",
      extra: usage.schema_filtering?.schema_tokens ? `${usage.schema_filtering.schema_tokens.toLocaleString("en-US")} schema tokens` : null,
      mono: tables.length > 0,
    },
    {
      name: "Generate",
      time: usage.generation_time,
      detail: GENERATION_MODEL,
      extra: usage.total_tokens ? `${usage.total_tokens.toLocaleString("en-US")} tokens` : null,
    },
    {
      name: "Validate",
      detail: validation?.enabled === false ? "Read-only check off" : "Read-only check",
    },
    {
      name: "Execute",
      time: exec?.seconds,
      detail: exec ? `BigQuery · ${formatBytes(exec.bytes)}${exec.cacheHit ? " (cached)" : ""}` : "BigQuery",
      extra: exec ? `${exec.totalRows.toLocaleString("en-US")} rows` : null,
    },
  ];
}

const DOT = {
  done: "bg-emerald-400",
  active: "bg-emerald-400 animate-pulse",
  pending: "bg-zinc-700",
  failed: "bg-rose-400",
};

export default function Pipeline({ turn, layout = "strip" }) {
  const running = turn.status === "generating" || turn.status === "executing";
  const elapsed = useElapsed(turn.startedAt, running);
  const states = stepStates(turn);
  const steps = pipelineSteps(turn);
  const total = turn.finishedAt ? (turn.finishedAt - turn.startedAt) / 1000 : elapsed;

  return (
    <section className="rounded-xl border border-line bg-panel p-4" aria-label="How the answer was produced">
      <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
        {running ? "Working" : "How it worked"} · {formatSeconds(total)}
        {running && turn.status === "generating" && " · retrieval and generation run as one call"}
      </p>
      <ol className={layout === "strip" ? "mt-3 grid gap-4 sm:grid-cols-5" : "mt-3 space-y-4"}>
        {steps.map((step, i) => (
          <li key={step.name} className={states[i] === "pending" ? "opacity-50" : ""}>
            <div className="flex items-center gap-2 text-sm">
              <span className={`size-2 rounded-full ${DOT[states[i]]}`} aria-hidden="true" />
              <span className="text-white">{step.name}</span>
              <span className="sr-only">({states[i]})</span>
              {step.time != null && states[i] === "done" && (
                <span className="ml-auto font-mono text-[11px] text-zinc-500">{formatSeconds(step.time)}</span>
              )}
            </div>
            <p className={`mt-1.5 text-[13px] leading-snug text-zinc-400 ${step.mono ? "font-mono text-[12px]" : ""}`}>{step.detail}</p>
            {step.extra && <p className="text-[13px] text-zinc-500">{step.extra}</p>}
          </li>
        ))}
      </ol>
    </section>
  );
}
