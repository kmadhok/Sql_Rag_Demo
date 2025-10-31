# SQL RAG Migration: Streamlit → FastAPI + React

This document explains how the repository evolved from the original Streamlit front end into a FastAPI back end with a React UI, while keeping the existing RAG pipeline intact.

## 1. Original State
- **Front end**: `app_simple_gemini.py` (Streamlit). The Query Search page was the main entry point.
- **Pipeline**: `simple_rag_simple_gemini.answer_question_simple_gemini` handled retrieval, schema injection, SQL generation, and validation.
- **LLM models**: hard-coded defaults in the Streamlit app and supporting modules, all residing under `rag_app/`.

## 2. Goals of the migration
- Expose the core pipeline via HTTP so other front ends (React, CLI, etc.) can reuse it.
- Preserve Streamlit while developing the new stack in parallel.
- Provide a chat-style UI that supports follow-up questions, execution, and result visualization.

## 3. FastAPI back end
- **Location**: `rag_app/api/main.py`
- **Endpoints**:
  - `POST /query/search`: Full RAG pipeline. Accepts the same options as Streamlit (k, hybrid search, schema injection, etc.) and returns `answer`, `sql`, `sources`, and `usage` metadata.
  - `POST /query/quick`: Concise answer path (default chat). Reuses the pipeline but skips SQL extraction/validation.
  - `POST /sql/execute`: Wraps BigQuery execution & safety checks.
  - `POST /saved_queries`, `GET /saved_queries`, `GET /saved_queries/{id}`: Save and retrieve executed SQL queries for the dashboard.
- **Startup**: Loads FAISS vector store, schema manager, and LookML join map at process start. Uses `services/sql_execution_service` and the new `services/saved_query_store` to share logic.
- **Model overrides**: The request payload can include `llm_model`. Concise chat uses `gemini-2.5-flash`; `@create` requests use `gemini-2.5-pro`.

## 4. React front end
- **Location**: `rag_app/frontend/` (Vite + React, MUI, Recharts).
- **Key components**:
  - `App.jsx`: Top-level tab layout with Introduction, Data, Chat, and Dashboard views.
  - `ChatInput`, `ChatHistory`, `ChatMessage`: Chat UI with advanced options, message transcript, and inline execution controls.
  - `Dashboard`: Lists saved queries, shows SQL, and renders either a table or a bar chart. Users can refresh, pick a saved query, and select columns for visualization.
  - `services/ragClient.js`: Fetch helpers for the FastAPI endpoints (`/query/search`, `/query/quick`, `/sql/execute`, `/saved_queries`).

### Running the stack locally
1. Install Python deps (from `requirements.txt`) and ensure BigQuery credentials are available.
2. In the repo root (or `rag_app/`):
   ```bash
   export GOOGLE_CLOUD_PROJECT=your-project
   export VECTOR_STORE_NAME=index_sample_queries_with_metadata_recovered
   uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
   ```
3. Front end:
   ```bash
   cd rag_app/frontend
   npm install
   npm run dev -- --host 127.0.0.1 --port 5173
   ```
4. Open `http://localhost:5173/`. Use `@create` for structured SQL requests and plain text for concise chat.

## 5. Shared pipeline & notable helpers
- `services/query_search_service.py` now exposes the entire Query Search flow so both Streamlit and FastAPI can import it.
- `simple_rag_simple_gemini.py` accepts an optional `llm_model` to patch the model per request.
- SQL extraction lives in `services/sql_extraction_service.py`; it returns SQL without Markdown fences.
- Saved queries are persisted under `saved_queries/` as JSON and can be loaded into the dashboard.

## 6. Feature parity with the Streamlit Query Search page
- Retrieval, schema injection, SQL generation, validation, and BigQuery execution behave identically because they still use the same helper modules.
- The React chat view handles follow-up questions, shows `sources` and `usage`, and lets users copy SQL or execute/dry-run inline.
- Dashboard demonstrates how saved queries can be visualized (table or bar chart) for future customization.

## 7. Next steps (optional)
- Wire in authentication/authorization for saved queries.
- Expand dashboard visualizations (line charts, scatter plots, etc.).
- Optimize prompt templates or add prompt editing tools in the UI.
- Add automated tests around the new FastAPI endpoints and the saved-query store.

