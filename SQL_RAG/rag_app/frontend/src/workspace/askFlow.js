import { analyzeResult, readableError } from "./analyzeResult.js";
import { extractSql } from "../utils/sqlExtractor.js";

export const GENERATION_MODEL = "gemini-2.5-pro";
export const MAX_BYTES_BILLED = 100_000_000;

export const DEFAULT_SETTINGS = {
  k: 20,
  hybrid_search: false,
  auto_adjust_weights: true,
  query_rewriting: false,
  sql_validation: true,
};

// Prior turns as plain text, so follow-ups ("only in the US") keep their context.
export function historyText(turns) {
  return turns
    .filter((t) => t.status === "done" || t.status === "error")
    .map((t) => `User: ${t.question}\nAssistant: ${t.summary || t.error || ""}${t.sql ? `\nSQL: ${t.sql.replace(/\s+/g, " ")}` : ""}`)
    .join("\n");
}

/**
 * Generate SQL for a question, run it, and describe the result.
 * Calls onUpdate(patch) as each stage completes; never throws.
 */
export async function askFlow({ question, history, settings }, api, onUpdate) {
  let search;
  try {
    search = await api.runQuerySearch({
      question,
      llm_model: GENERATION_MODEL,
      gemini_mode: false,
      ...DEFAULT_SETTINGS,
      ...settings,
      agent_type: "create",
      conversation_context: history,
    });
  } catch (err) {
    onUpdate({ status: "error", failedStep: "generate", error: readableError(err), finishedAt: Date.now() });
    return;
  }

  const sql = search.cleaned_sql || search.sql || extractSql(search.answer || "");
  const generated = { sql, answer: search.answer, usage: search.usage || null, sources: search.sources || [] };
  if (!sql) {
    onUpdate({ ...generated, status: "error", failedStep: "generate", error: "The model answered without writing a query. Try asking for specific numbers.", finishedAt: Date.now() });
    return;
  }
  onUpdate({ ...generated, status: "executing" });

  let exec;
  try {
    exec = await api.executeSql({ sql, dry_run: false, max_bytes_billed: MAX_BYTES_BILLED });
  } catch (err) {
    onUpdate({ status: "error", failedStep: "execute", error: readableError(err), finishedAt: Date.now() });
    return;
  }
  if (!exec || exec.success === false) {
    const reason = exec?.error_message || exec?.validation_message || "BigQuery rejected the query.";
    onUpdate({ status: "error", failedStep: "execute", error: reason, finishedAt: Date.now() });
    return;
  }

  const rows = exec.data || [];
  const analysis = analyzeResult(rows);
  onUpdate({
    status: "done",
    rows,
    analysis,
    summary: analysis.summary,
    execution: {
      totalRows: exec.total_rows ?? rows.length,
      seconds: exec.execution_time,
      bytes: exec.bytes_processed,
      cacheHit: exec.cache_hit,
    },
    finishedAt: Date.now(),
  });
}
