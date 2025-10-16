# Query Search (Simple Mode) — End‑to‑End Execution Flow

This document describes, in detail, what happens inside the app when a user asks a question on the Query Search page in Simple mode.

It covers state management, retrieval, schema injection, answer generation, SQL extraction, validation, and BigQuery execution, and notes which parts are LLM‑based vs. deterministic (regex/sqlparse/schema lookups).

---

## High‑Level Sequence

1) Input + New Search kickoff
2) Retrieval from FAISS
3) Schema injection (relevant tables + FQNs)
4) Prompt build and LLM answer generation
5) SQL extraction from answer
6) Persistent SQL execution interface (validate + execute + results)

---

## Detailed Flow

### 1) Input + New Search Kickoff
- File: `app_simple_gemini.py`
- Location: Query Search page, Simple mode
- When the user clicks “Search”:
  - We clear any previous SQL/execution state to ensure a fresh run:
    - Keys removed: `sql_execution_completed`, `sql_executing`, `sql_execution_error`, `sql_execution_result`, `extracted_sql`.
  - A simple spinner (`st.spinner("Working...")`) displays during the pipeline (Advanced shows a step panel).
  - Simple mode uses defaults (no extra toggles); in particular:
    - `k = 4` (documents retrieved)
    - Hybrid/off, Gemini mode/off (unless Advanced is enabled)

### 2) Retrieval (Vector Search)
- File: `app_simple_gemini.py` → loads vector store via `load_vector_store` and `FAISS` similarity search.
- Embedding provider: configured via `utils.embedding_provider` (OpenAI by default), but the search itself is a FAISS similarity query.
- Timeout safety is in place for embedding calls where applicable; Simple mode uses standard vector search only (no BM25 fusion unless Advanced+Hybrid enabled).

### 3) Schema Injection (Relevant Tables + FQNs)
- File: `schema_manager.py`
- Purpose: build a compact schema snippet to include in the prompt, focusing only on tables relevant to the question and retrieved content.
- How tables are discovered:
  - LLM‑first extraction for SQL‑looking text via `LLMSQLAnalyzer` (Gemini) with a cap:
    - Env: `SCHEMA_DOC_LIMIT` (default 20) limits how many doc chunks we scan to avoid excessive calls.
    - Falls back to regex/sqlparse when the text is not clearly SQL or LLM fails.
  - Normalization + de‑duplication performed in `SchemaManager`.
- Formatting the schema:
  - `SchemaManager.get_relevant_schema(filtered_tables)` returns a deterministic formatted list of columns/datatypes for each table.
  - FQN mapping reuse: we reuse the same list of discovered tables to build a BigQuery FQN mapping (no second extraction pass).
  - Note: In Simple mode the UI doesn’t render the schema browser; the schema snippet is injected into the LLM prompt only.

LLM vs regex here:
- Extraction is LLM‑first (Gemini) with a doc cap, falling back to regex/sqlparse if needed.
- Formatting and FQN mapping are deterministic against the CSV schema.

### 4) Prompt Build + LLM Answer Generation
- File: `simple_rag_simple_gemini.py` → `answer_question_simple_gemini`
- Model: `GEMINI_MODEL` = `gemini-2.5-flash-lite` (fast, default for Query Search).
- Prompt includes:
  - The user question
  - The compact relevant schema (with FQNs where available)
  - Retrieved context (deduplicated/condensed where applicable)
- Metrics captured:
  - Retrieval time (seconds)
  - Generation time (seconds)
  - Token usage estimates (prompt/completion/total)

### 5) SQL Extraction (from Answer)
- File: `app_simple_gemini.py`
- After the answer renders, we extract SQL and store it in session state:
  - Preferred: `BigQueryExecutor.extract_sql_from_text(answer)` if executor is ready.
  - Fallback: regex extraction of code‑fenced SQL blocks (```sql … ``` or ``` … ```), with a sanity check (must start with SELECT/WITH and contain FROM/AS).
- On success, we set `st.session_state.extracted_sql`. This enables the persistent execution interface.

### 6) Persistent SQL Execution Interface
- File: `app_simple_gemini.py` → `display_sql_execution_interface`
- Always rendered below the answer if `extracted_sql` is present (both Simple and Advanced).
- Lazy BigQuery initialization (Simple mode):
  - Project/Dataset resolve from env (`BIGQUERY_PROJECT_ID` or `GOOGLE_CLOUD_PROJECT`, with dataset default `bigquery-public-data.thelook_ecommerce`).
- Safety validation (deterministic):
  - `BigQueryExecutor.validate_sql_safety(sql)` rejects write ops and enforces constraints.
- Execute form (Streamlit form):
  - Simple mode: shows only a submit button (Execute). Dry run and cost limits are hidden and default to safe values.
  - Advanced mode: shows execution info and an expander for Dry Run + Max Bytes Billed.
  - Submit triggers `execute_sql_callback()` (runs before rerun according to Streamlit’s form pattern).
- Execution details:
  - File: `core/bigquery_executor.py` → `execute_query(sql, dry_run=False, max_bytes_billed=...)`
  - Creates a `QueryJobConfig`, executes with timeout, collects metrics:
    - `bytes_processed`, `bytes_billed`, `cache_hit`, `execution_time`, `job_id`.
  - Dry run: returns stats only (no data frame, no table render).
- Results rendering (outside the form):
  - Displays rows, time, data processed/billed, and a dataframe if present.
  - CSV download is available (outside the form to satisfy Streamlit constraints).
  - “Clear SQL” button resets execution and extraction state.

---

## SQL Validation Path (Simple mode)
- Validation is on by default (even though details are hidden in Simple UI).
- File: `simple_rag_simple_gemini.py` → `validate_sql_query` (Schema Strict)
- Extraction (LLM‑based):
  - Uses a single, comprehensive LLM parse via `LLMSQLAnalyzer.analyze_sql_comprehensive(sql)` (model: `gemini-2.5-flash-lite`) to get both tables and columns.
- CTE filtering:
  - The validator detects `WITH name AS (...)` CTEs and excludes those names (case‑insensitive) from table and column validation.
- Deterministic checks:
  - Tables: `SchemaManager.get_table_info(table)` or `schema_df` lookup.
  - Columns: `SchemaManager.get_table_columns(table)` or `schema_df` lookup.
  - BigQuery rule checks (e.g., DATE vs TIMESTAMP functions) are rule‑based.
- Output used for metrics/UX; the Simple UI just shows the answer and SQL, but the execution form remains available even if validation warns.

LLM vs regex here:
- Parsing (tables/columns): LLM comprehensive call (Gemini) for accuracy on complex SQL (CTEs, windows, nested SELECTs).
- Validation decisions: deterministic against your schema; no LLM is used to “decide” correctness.

---

## State Management
- New search clears: `sql_execution_completed`, `sql_executing`, `sql_execution_error`, `sql_execution_result`, `extracted_sql`.
- SQL extraction sets: `extracted_sql` upon success.
- Execution callback sets: `sql_executing`, `sql_execution_result` or `sql_execution_error`, and `sql_execution_completed`.
- Clear SQL button removes: `extracted_sql`, `sql_execution_result`, `sql_execution_error`, `sql_execution_completed`.

---

## Models + Config
- Answer generation (Query Search): `gemini-2.5-flash-lite` (fast default).
- SQL parsing (LLM extractor): `gemini-2.5-flash-lite` by default (config in `core/llm_sql_analyzer.py`).
- Env vars:
  - `SCHEMA_DOC_LIMIT` — caps doc chunks scanned for schema extraction (default 20).
  - `BIGQUERY_PROJECT_ID`, `BIGQUERY_DATASET` — BigQuery context (Simple uses these implicitly).
  - `UI_ADVANCED_DEFAULT` — set to `1/true` to start in Advanced mode by default.

---

## Performance Levers
- Keep Simple mode defaults (k=4, Hybrid off) for fastest response.
- `SCHEMA_DOC_LIMIT` keeps schema extraction affordable by limiting LLM calls.
- Validator uses a single comprehensive LLM parse per SQL (fewer calls) and filters CTEs to avoid false errors.

---

## Error Handling Notes
- If no SQL is found in the answer, the execution interface won’t render; prompts can be tuned to ensure the answer includes a ```sql code block.
- If BigQuery is unavailable, execution shows a clear warning; Simple mode keeps the UI minimal.
- Streamlit form constraints are respected: only the submit lives inside the form; other buttons/downloads live outside.

---

## Differences from Advanced Mode (Short)
- Simple: Answer → SQL → Execute → Results only; spinner; executor settings hidden.
- Advanced: Adds toggles (Gemini/Hybrid/Rewriting), BigQuery settings, schema browser/panels, step panel, validation and token metrics, execution controls.

---

## Key Files + Functions
- Query Search UX: `app_simple_gemini.py`
- RAG + Answer Generation: `simple_rag_simple_gemini.py` → `answer_question_simple_gemini`
- Schema Manager: `schema_manager.py` → extraction + formatting + FQN mapping
- SQL Parsing (LLM): `core/llm_sql_analyzer.py` (Gemini structured outputs)
- SQL Validation: `core/sql_validator.py` → `validate_sql_query`
- BigQuery Execution: `core/bigquery_executor.py` → `execute_query`

---

## TL;DR
- Simple mode keeps the UI minimal while still doing the full retrieval → schema → LLM answer → SQL extraction → validation → execution pipeline.
- LLM is used to parse complex SQL (especially CTEs); actual validation is deterministic against your schema.
- We minimized LLM calls (doc caps, comprehensive parse, reuse for FQNs) and fixed CTE false positives.
