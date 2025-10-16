# Latency Strategies and Model Choices

This document catalogs the concrete changes we made to reduce end‑to‑end latency and documents the model choices (and trade‑offs) that helped. It complements `docs/latency.md` (root causes and per‑stage timing) with a change log you can skim quickly.

---

## Changes Implemented

- Comprehensive SQL parse for validation
  - Before: separate LLM calls for tables and columns per SQL statement
  - After: single `analyze_sql_comprehensive(sql)` call returns both tables and columns
  - Impact: fewer LLM round‑trips, less variance, simpler logic

- Robust CTE filtering (case‑insensitive)
  - Exclude CTE names (e.g., `WITH my_cte AS (...)`) from table/column validation
  - Prevents false “table not found” on CTE aliases
  - Implemented in both extraction and validation stages

- Reused table list for FQN mapping
  - Before: schema extraction pass, then re‑extraction for FQN mapping
  - After: reuse the same derived table list for FQNs
  - Impact: removes an entire set of LLM extractions

- Limited document scans for schema extraction
  - Env: `SCHEMA_DOC_LIMIT` (default 20) caps how many retrieved chunks we scan with LLM
  - Impact: reduces bursty extractions on SQL‑heavy results

- Faster default parsing model
  - SQL parsing/structured extraction defaulted to `gemini-2.5-flash-lite`
  - Impact: noticeably faster LLM parsing while retaining good accuracy for CTEs and complex SQL

- Chat pipeline fast path
  - Reduced retrieval `k` (20) and switched schema table extraction to regex (fast)
  - Reused derived tables for FQNs (no second extraction pass)

- Step/status panel (Advanced mode)
  - Surfaces measured times (retrieval, generation, validation) so we can reason about regressions

- Batch runner timings
  - `scripts/run_batch_questions.py` now records per‑variant timings in results.jsonl
  - Fields: `pipeline_seconds`, `retrieval_seconds`, `generation_seconds`, `validation_seconds`, BigQuery `execution.execution_time`

---

## Configuration Knobs

- `SCHEMA_DOC_LIMIT` (int, default 20): max retrieved chunks scanned for schema extraction
- `UI_ADVANCED_DEFAULT` (0/1): default Advanced UI mode (Simple is faster by default)
- `BIGQUERY_PROJECT_ID`, `BIGQUERY_DATASET`: execution context; can affect BigQuery job latency
- Proposed: `LLM_SQL_MODEL` to override the parsing model globally (see modular design)

---

## Model Choices (Current Defaults)

- Answer generation (Query Search): `gemini-2.5-flash-lite`
- SQL parsing (extraction / validation): `gemini-2.5-flash-lite`
- Chat generation: `gemini-2.5-flash`

Rationale:
- `flash-lite` is fast and accurate enough for structured parsing and many SQL generation tasks.
- Chat benefits from the non‑lite flash for slightly stronger generation quality; switchable if needed.

---

## Additional Opportunities (Optional)

- Batch schema extraction: concatenate top‑K SQL snippets into one prompt and ask the LLM once for the unique table set
- Schema mode switch: `auto` (LLM batch), `regex` (fast), `off` (no injection)
- Smart‑K retrieval: start small and increase only on need (e.g., confidence triggers or empty result sets)
- Aggressive caching: keep `llm_sql_cache/` warm; reuse extracted table lists across runs

---

## How to Compare Approaches

Use the batch runner variants:

- `current` — schema injection + validation
- `no_schema` — no schema injection, manual validation afterward
- `schema_only` — schema injection only
- `minimal` — neither

Timings are emitted in each variant’s `results.jsonl`.
