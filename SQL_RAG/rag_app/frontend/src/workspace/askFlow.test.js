import { describe, expect, it, vi } from "vitest";
import { askFlow, historyText, GENERATION_MODEL, MAX_BYTES_BILLED } from "./askFlow.js";

const SQL = "SELECT first_name, last_name, SUM(sale_price) AS total_order_value FROM `bigquery-public-data.thelook_ecommerce.users`";
const ROWS = [
  { first_name: "Jonathan", last_name: "Kennedy", total_order_value: 2052.33 },
  { first_name: "Jonathon", last_name: "Barnes", total_order_value: 1924.63 },
];

function fakeApi({ search, exec } = {}) {
  return {
    runQuerySearch: vi.fn(async () => (search instanceof Error ? Promise.reject(search) : search ?? { cleaned_sql: SQL, answer: "…", usage: { total_tokens: 10 }, sources: [{ content: "x", metadata: {} }] })),
    executeSql: vi.fn(async () => (exec instanceof Error ? Promise.reject(exec) : exec ?? { success: true, data: ROWS, total_rows: 2, execution_time: 1.2, bytes_processed: 1000, cache_hit: false })),
  };
}

async function run(api, input = {}) {
  const updates = [];
  await askFlow({ question: "Top users", history: "", settings: {}, ...input }, api, (u) => updates.push(u));
  return updates;
}

describe("askFlow", () => {
  it("generates SQL, runs it, and finishes with an analysed result", async () => {
    const api = fakeApi();
    const updates = await run(api);
    expect(updates.map((u) => u.status)).toEqual(["executing", "done"]);
    expect(updates[0]).toMatchObject({ sql: SQL, usage: { total_tokens: 10 } });
    expect(updates[1]).toMatchObject({
      rows: ROWS,
      summary: "Found 2 rows. Jonathan Kennedy leads at $2,052.",
      execution: { totalRows: 2, seconds: 1.2, bytes: 1000, cacheHit: false },
    });
  });

  it("always asks for SQL (no @create needed) and passes settings and history", async () => {
    const api = fakeApi();
    await run(api, { history: "User: earlier", settings: { k: 5, query_rewriting: true } });
    expect(api.runQuerySearch).toHaveBeenCalledWith(expect.objectContaining({
      question: "Top users",
      agent_type: "create",
      llm_model: GENERATION_MODEL,
      k: 5,
      query_rewriting: true,
      sql_validation: true,
      conversation_context: "User: earlier",
    }));
    expect(api.executeSql).toHaveBeenCalledWith({ sql: SQL, dry_run: false, max_bytes_billed: MAX_BYTES_BILLED });
  });

  it("falls back to raw sql, then to SQL extracted from the answer", async () => {
    const fromRaw = await run(fakeApi({ search: { sql: "SELECT 1", answer: "" } }));
    expect(fromRaw[0].sql).toBe("SELECT 1");
    const fromAnswer = await run(fakeApi({ search: { answer: "Here you go:\n```sql\nSELECT 2\n```" } }));
    expect(fromAnswer[0].sql).toMatch(/SELECT 2/);
  });

  it("reports a generation error without running anything", async () => {
    const api = fakeApi({ search: new Error('{"detail":"RAG pipeline returned no result."}') });
    const updates = await run(api);
    expect(updates).toHaveLength(1);
    expect(updates[0]).toMatchObject({ status: "error", failedStep: "generate" });
    expect(updates[0].error).toMatch(/couldn't produce a query/);
    expect(api.executeSql).not.toHaveBeenCalled();
  });

  it("reports an error when the model returns no SQL", async () => {
    const updates = await run(fakeApi({ search: { answer: "I am not sure." } }));
    expect(updates[0]).toMatchObject({ status: "error", failedStep: "generate" });
  });

  it("treats success:false from BigQuery as an execution error and keeps the SQL", async () => {
    const updates = await run(fakeApi({ exec: { success: false, error_message: "Unrecognized name: foo" } }));
    expect(updates.map((u) => u.status)).toEqual(["executing", "error"]);
    expect(updates[0].sql).toBe(SQL);
    expect(updates[1]).toMatchObject({ failedStep: "execute", error: "Unrecognized name: foo" });
  });

  it("uses the validation message when BigQuery gives no error message", async () => {
    const updates = await run(fakeApi({ exec: { success: false, validation_message: "Only SELECT is allowed" } }));
    expect(updates[1].error).toBe("Only SELECT is allowed");
  });

  it("reports network failures during execution in plain language", async () => {
    const updates = await run(fakeApi({ exec: new TypeError("Failed to fetch") }));
    expect(updates[1]).toMatchObject({ status: "error", failedStep: "execute" });
    expect(updates[1].error).toMatch(/Can't reach the API/);
  });

  it("handles an empty result set", async () => {
    const updates = await run(fakeApi({ exec: { success: true, data: [], total_rows: 0 } }));
    expect(updates[1]).toMatchObject({ status: "done", summary: "The query returned no rows.", execution: { totalRows: 0 } });
  });
});

describe("historyText", () => {
  it("includes finished turns with their summary and SQL, and skips in-flight ones", () => {
    const text = historyText([
      { question: "Top users", status: "done", summary: "Found 8 rows.", sql: "SELECT\n  1" },
      { question: "Bad one", status: "error", error: "Boom" },
      { question: "Pending", status: "generating" },
    ]);
    expect(text).toBe("User: Top users\nAssistant: Found 8 rows.\nSQL: SELECT 1\nUser: Bad one\nAssistant: Boom");
  });

  it("is empty for no turns", () => {
    expect(historyText([])).toBe("");
  });
});
