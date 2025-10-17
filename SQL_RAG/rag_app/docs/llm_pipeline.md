# LLM Usage in the Pipeline and Modularity Plan

This document describes where and how LLMs are used throughout the system, the current model choices, and a plan to make LLM usage modular so different models or providers can be assigned to specific roles (parsing vs generation).

---

## Where LLMs Are Used Today

1) Query rewriting (optional, Advanced/Batch)
   - File: `simple_rag_simple_gemini.py` (query rewriting block)
   - Purpose: Improve retrieval with domain terminology
   - Model: Gemini via `create_query_rewriter()` (auto‑select), optional

2) Schema injection — table discovery from docs + question
   - File: `schema_manager.py` → `extract_tables_from_content`, `extract_tables_from_documents`
   - Purpose: Identify likely real tables to include in the schema prompt block
   - Behavior: LLM‑first for SQL‑looking text (Gemini structured extraction); regex fallback otherwise

3) SQL generation (answer creation)
   - File: `simple_rag_simple_gemini.py` → `answer_question_simple_gemini`
   - Purpose: Produce the final SQL and explanation
   - Model: `gemini-2.5-flash-lite` (Query Search); `gemini-2.5-flash` (Chat)

4) SQL parsing for validation
   - File: `core/llm_sql_analyzer.py`, `core/sql_validator.py`
   - Purpose: Parse tables + columns (CTEs, nested SELECTs) before deterministic checks
   - Behavior: single comprehensive structured extraction
   - Model: `gemini-2.5-flash-lite`

5) (Optional) LookML join context
   - File: `app_simple_gemini.py` (LookML block)
   - Purpose: Provide best‑practice join hints; no LLM used here

---

## Deterministic vs LLM Responsibilities

- Deterministic:
  - FAISS retrieval
  - Schema formatting / FQN map (from CSV)
  - BigQuery safety checks (write‑ops, timeouts, size caps)
  - Validation decisions (table/column existence; BigQuery rule checks)

- LLM:
  - Complex SQL parsing (tables/columns) including CTEs and window functions
  - Generation (natural language → executable SQL)
  - Optional rewriting (improve retrieval queries)

---

## Current Model Choices

- Parsing & validation: `gemini-2.5-flash-lite`
- Query Search generation: `gemini-2.5-flash-lite`
- Chat generation: `gemini-2.5-flash`

Rationale: `flash-lite` reduces latency and cost without sacrificing much on structured parsing.

---

## Modularity Plan: Separate Models per Role (Implemented)

We now support selecting different Gemini models per pipeline step using environment variables and a small registry.

### Config Surface (env vars)

- `LLM_PARSE_MODEL`   — model for parsing/structured extraction (default: `gemini-2.5-flash-lite`)
- `LLM_GEN_MODEL`     — model for SQL generation (default: `gemini-2.5-pro`)
- `LLM_REWRITE_MODEL` — model for query rewriting (default: falls back to `LLM_PARSE_MODEL` or `gemini-2.5-flash-lite`)
- `LLM_CHAT_MODEL`    — model for chat responses (default: `gemini-2.5-flash-lite`)

Example (.env):

```
LLM_GEN_MODEL=gemini-2.5-pro
LLM_PARSE_MODEL=gemini-2.5-flash-lite
LLM_REWRITE_MODEL=gemini-2.5-flash-lite
LLM_CHAT_MODEL=gemini-2.5-flash-lite
```

### LLM Registry

`llm_registry.py` exposes a simple interface:

```python
from llm_registry import get_llm_registry
reg = get_llm_registry()
reg.get_generator()  # SQL generation client (LLM_GEN_MODEL)
reg.get_parser()     # Parsing client (LLM_PARSE_MODEL)
reg.get_chat()       # Chat client (LLM_CHAT_MODEL)
```

### Call Sites Updated

- `core/llm_sql_analyzer.py` now defaults to `LLM_PARSE_MODEL`.
- `query_rewriter.py` defaults to `LLM_REWRITE_MODEL` (or `LLM_PARSE_MODEL`).
- `simple_rag_simple_gemini.py` uses the registry for SQL generation.
- `app_simple_gemini.py` (chat) uses the registry for chat generation.

This lets you run “Gemini 2.5 Pro” for SQL generation and “Gemini 2.5 Flash‑Lite” for everything else by setting the env vars above.

---

## Testing & Observability

- Batch runner variants (`current`, `no_schema`, `schema_only`, `minimal`) + timings logged to `results.jsonl`.
- Compare `pipeline_seconds`, `generation_seconds`, and `validation_seconds` across roles/models.
- Keep `llm_sql_cache/` warm to reduce structured parse latency.

---

## Summary

- Today we use Gemini for parsing and generation; parsing leverages structured outputs and a single comprehensive call per SQL.
- The pipeline is already role‑separated in practice (parsing vs generation). With a tiny configuration layer, we can make models per role switchable without large refactors.
- This unlocks experimentation (e.g., a cheaper/faster parser with a stronger generator) to further optimize latency and quality.
