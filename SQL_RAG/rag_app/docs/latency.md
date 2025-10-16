# Latency Deep‑Dive and Current Understanding

This document explains where time is spent in the system, why certain queries feel slow, and what we’ve changed or can change to improve responsiveness.

It reflects real observations from recent runs and ties them to the code paths and configuration toggles in the app.

---

## TL;DR

- Biggest contributor: LLM calls for SQL parsing (tables/columns) during Schema Injection and SQL Validation.
- Secondary contributors: query embedding for FAISS (one embedding call per query), BigQuery execution time, and network overhead.
- UI/Streamlit overhead is negligible compared to LLM + network time.
- Recent fixes: comprehensive LLM parse for validation; CTE filtering; limited doc scans; table‑list reuse for FQNs. These reduce duplicated LLM calls and false errors.

---

## Where Time Goes (By Pipeline Stage)

### 1) Query Embedding + FAISS Retrieval
- Purpose: embed the user query and run FAISS similarity search to get relevant chunks.
- Components: `utils.embedding_provider` (embeds the query), FAISS index lookup.
- Latency: typically ~0.4–1.2s (one remote call to the embedding provider + fast FAISS search).
- Notes: no LLM here; one network call per query.

### 2) Schema Injection (Relevant Tables + FQNs)
- Purpose: build a compact schema block for the LLM prompt.
- Main cost: table extraction from top‑K retrieved docs and the question.
- Default behavior: LLM‑first extraction using `LLMSQLAnalyzer` (Gemini), capped by `SCHEMA_DOC_LIMIT` (default 20), with regex/sqlparse fallback.
- Past bottleneck: duplicate extraction pass for the FQN mapping (re‑extracting again). Fixed by reusing the same table list.
- Latency impact: depends on how many chunks we scan and whether they look like SQL. Typical single‑digit seconds worst‑case; now reduced via caps and reuse.

### 3) Answer Generation (LLM)
- Purpose: generate the natural‑language answer + SQL.
- Model: `gemini-2.5-flash-lite` in Query Search (fast).
- Latency: usually ~0.5–1.5s for the responses observed.

### 4) SQL Extraction (from Answer)
- Purpose: find the SQL in the LLM’s response.
- Behavior: executor extraction if available; otherwise regex on fenced code blocks.
- Latency: local, negligible.

### 5) SQL Validation (Tables/Columns vs Schema)
- Purpose: ensure the SQL references tables/columns that exist; provide BigQuery guidance.
- Main cost: parsing SQL to discover tables + columns.
- Recent change: use a single comprehensive LLM parse (`analyze_sql_comprehensive`) instead of separate calls for tables and columns.
- CTE filtering: exclude CTE names (case‑insensitive) from validation to prevent false “table not found”.
- Latency impact: still LLM‑backed parsing (usually seconds), but reduced by eliminating duplicate calls. Regex fallback is available but less robust on complex SQL.

### 6) BigQuery Execution (Optional)
- Purpose: run the generated SQL.
- Latency: depends on query + dataset size; recent examples ~1.5–2.0s.
- Notes: dry‑run is fast and returns bytes processed estimate only.

---

## Why Some Queries Felt Slow

- Repeated LLM extraction passes:
  - Schema Injection scanned multiple chunks with LLM and then re‑extracted for FQNs.
  - Validation extracted tables and columns separately per SQL statement.
- Many SQL‑looking snippets:
  - Retrieved docs often contain code snippets; each triggers the LLM extractor unless capped.
- Complex SQL with CTEs/nesting:
  - Regex struggles and falls back to LLM, which is correct but slower.

---

## What We Changed (Performance)

- Validator: single comprehensive LLM parse instead of separate table/column passes.
- Validator: robust CTE filtering (case‑insensitive) so CTEs are never validated against schema.
- Schema Injection: reuse the same table list for FQN mapping (avoid duplicate extraction pass).
- Schema Injection: cap doc scans via `SCHEMA_DOC_LIMIT` (default 20).
- Chat: reduced retrieval `k` and switched to regex for schema extraction (fast path).
- SQL parsing model: default to `gemini-2.5-flash-lite` for faster structured parsing.

---

## Configuration Knobs

- `SCHEMA_DOC_LIMIT` (int, default 20): max doc chunks scanned with LLM for schema extraction.
- `UI_ADVANCED_DEFAULT` (0/1): whether the app starts in Advanced mode; Simple is faster.
- `BIGQUERY_PROJECT_ID`, `BIGQUERY_DATASET`: determine execution context; can impact BigQuery performance depending on data locality.
- `LLM_SQL_MODEL` (proposed): wire this to override the model used by `LLMSQLAnalyzer` without code changes.

---

## Suggested Strategies to Reduce Latency Further

- Batch table extraction for schema: concatenate top‑K SQL snippets and ask LLM once for unique tables.
- Make schema extraction mode configurable:
  - `auto` (LLM batch), `regex` (fast), `off` (no schema injection).
- Smart K: start with lower K, expand only on need (e.g., confidence triggers or empty result sets).
- Aggressive caching:
  - Keep LLM parse results (`llm_sql_cache/`) keyed by the SQL text.
  - Cache table lists for common queries and share across FQN mapping.

---

## Observability Tips

- Enable DEBUG logs for `schema_manager`, `core.sql_validator`, `simple_rag_simple_gemini` to see each phase’s timings.
- Advanced mode shows a step panel with measured durations (retrieval, schema injection, generation, validation).
- Compare runs with different `SCHEMA_DOC_LIMIT` values and K to understand trade‑offs.

---

## Bottom Line

- LLM parsing delivers correctness for CTEs/complex SQL, but network round‑trips are the primary latency driver.
- The recent changes reduce redundant LLM work and protect against false errors, improving both speed and reliability.
- Additional batching and configurable modes can take us further if needed.
