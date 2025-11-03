# SQL RAG FastAPI + React Architecture

This guide explains how the FastAPI backend and React frontend stitch together, keeping the original `app_simple_gemini.py` Streamlit app in mind. Use it as a map for finding the code that drives each request and UI action.

## 1. How We Got Here

- **Streamlit baseline:** `app_simple_gemini.py` is the monolithic UI. It loads FAISS, schema metadata, and executes queries directly through helpers such as `run_query_search` and `run_sql_execution`.
- **Migration goal:** Move the non-UI pipeline into reusable services and expose them through HTTP so that a React client (and any future clients) can call the same logic.
- **Result:** Streamlit, FastAPI, and React now depend on the same services under `rag_app/services/` and `rag_app/data/`.

## 2. Backend Overview (FastAPI)

**Entry point:** `api/main.py`

### Startup lifecycle

`startup_event` (lines 190-207) mirrors the initialization in `app_simple_gemini.py`:

| Responsibility | FastAPI code | Streamlit equivalent |
| -------------- | ------------ | -------------------- |
| Load FAISS vector store | `data.app_data_loader.load_vector_store` | `load_vector_store` call during Streamlit boot |
| Load schema manager | `load_schema_manager` | `SCHEMA_MANAGER` setup in Streamlit |
| Load LookML safe-join map | `load_lookml_safe_join_map` | `LOOKML_SAFE_JOIN_MAP` in Streamlit |
| Prepare BigQuery executor | `initialize_executor` | `initialize_executor` when Streamlit executes SQL |

All objects are cached in module-level globals so each request reuses warm resources.

### Endpoints and their services

| Route | Purpose | Implementation | Service layer | Notes |
| ----- | ------- | -------------- | ------------- | ----- |
| `GET /health` | Quick status check for dependencies | `api/main.py:231-239` | — | Verifies vector store, schema manager, lookml map, executor |
| `POST /query/search` | Full Query Search pipeline (structured `@create`) | `api/main.py:242-328` | `services/query_search_service.py` | Accepts advanced knobs (hybrid search, validation, weights) and uses `services/sql_extraction_service` for cleaned SQL |
| `POST /query/quick` | Lightweight chat-style answer | `api/main.py:380-423` | `services/query_search_service.py` | Runs same RAG path with simplified settings (no SQL validation) |
| `POST /sql/execute` | Run or dry-run SQL | `api/main.py:331-377` | `services/sql_execution_service.py` | Validates SQL safety before calling BigQuery |
| `POST /saved_queries`<br>`GET /saved_queries`<br>`GET /saved_queries/{id}` | Persist and fetch executed SQL + preview data | `api/main.py:426-464` | `services/saved_query_store.py` | Saved as JSON files under `rag_app/saved_queries/` |
| `POST /dashboards`<br>`GET /dashboards`<br>`GET /dashboards/{id}`<br>`PATCH /dashboards/{id}`<br>`POST /dashboards/{id}/duplicate`<br>`DELETE /dashboards/{id}` | CRUD for dashboard layouts | `api/main.py:470-543` | `services/dashboard_store.py` | Stores layout JSON in `rag_app/dashboards/` |

All routes depend on the same `run_query_search` and `run_sql_execution` helpers that Streamlit imports, ensuring behavior parity.

### Response transformation: backend vs frontend expectations

**Important:** The `/sql/execute` endpoint returns a **flat structure** with fields at the top level, but the React frontend expects a **nested structure** for easier component rendering.

**Backend response** (`api/main.py:370-377`):
```json
{
  "success": true,
  "data": [{"col1": "val1", "col2": "val2"}],
  "total_rows": 150,
  "job_id": "...",
  "bytes_processed": 12345,
  "execution_time": 1.23
}
```

**Frontend transformation** (`App.jsx:391-404`):
```javascript
const transformedResult = {
  data: response.data || [],
  columns: response.data?.length > 0 ? Object.keys(response.data[0]) : [],
  row_count: response.total_rows || 0,  // ← Renamed from total_rows
  job_id: response.job_id,
  bytes_processed: response.bytes_processed,
  // ... other fields preserved
};
```

This transformation happens in `handleExecute` so that `ChatMessage.jsx` can easily access `result.row_count`, `result.columns`, and `result.data` without needing to know about the backend's field names.

### Shared service responsibilities

- **`services/query_search_service.py`** – wraps `answer_question_simple_gemini` so callers provide `QuerySearchSettings`. This is the same logic `app_simple_gemini.py` uses when the user submits a question.
- **`services/sql_execution_service.py`** – safety check + BigQuery execution. Streamlit invokes this in `handle_sql_execution`; FastAPI calls it from `/sql/execute`.
- **`services/sql_extraction_service.py`** – extracts SQL from responses using regex or Gemini. `/query/search` uses it to emit `cleaned_sql`, while Streamlit invokes `extract_sql_from_text` after generating an answer.
- **`data/app_data_loader.py`** – loading routines for vector stores, schema, LookML, and cached analytics. Both entry points call the same functions.
- **`services/saved_query_store.py` & services/dashboard_store.py`** – filesystem persistence used by Streamlit’s dashboards (if enabled) and the React dashboard.

## 3. Frontend Overview (React)

**Entry point:** `frontend/src/App.jsx`

`App` replaces Streamlit UI tabs with React components but keeps the same pipeline semantics:

- **Chat tab:** Handles both structured `@create` and conversational prompts.
- **Dashboard tab:** Visualizes saved queries, similar to the Streamlit dashboard pages.
- **Data/Introduction tabs:** Static content mirrors Streamlit informational pages.

### Key components and helpers

| Area | File(s) | Responsibilities | Backend touchpoints |
| ---- | ------- | ---------------- | ------------------- |
| API client | `frontend/src/services/ragClient.js` | Wraps `fetch` calls to all FastAPI endpoints. Automatically strips trailing slashes and reads `VITE_API_BASE_URL`. | `/query/search`, `/query/quick`, `/sql/execute`, `/saved_queries`, `/dashboards` |
| Chat flow | `App.jsx`, `components/ChatInput.jsx`, `components/ChatHistory.jsx`, `components/ChatMessage.jsx` | Splits `@create` vs. quick chat. Serializes conversation history (mimicking Streamlit conversation context). Executes SQL, saves queries, displays usage metrics. | `/query/search`, `/query/quick`, `/sql/execute`, `/saved_queries` |
| Dashboard | `components/Dashboard.jsx` + related modals/panels | Loads dashboards, edits layout, adds charts, exports data. Debounced autosave to the backend store. | `/dashboards`, `/saved_queries` |
| SQL extraction | `utils/sqlExtractor.js` | Client-side mirror of `sql_extraction_service`. Used when backend didn't send `cleaned_sql`. | Local only |
| Theming & templates | `utils/themes.js`, `utils/dashboardTemplates.js` | UI polish and dashboard scaffolding. | Local only |

### Streamlit widget → React component mapping

| Streamlit Widget | React Component | Key Differences |
| ---------------- | --------------- | --------------- |
| `st.chat_input()` | `ChatInput.jsx` | Streamlit's is built-in with automatic state management; React's is custom with manual `value` and `onChange` handling |
| `st.chat_message()` | `ChatMessage.jsx` | Streamlit auto-formats with avatar; React uses custom `MessageContainer` with `U`/`A` letter avatars |
| `st.expander()` | Collapsible panels (e.g., `SourceList`, `ExecutionPanel`) | Streamlit's is built-in; React uses `useState` for `isExpanded` toggle |
| `st.dataframe()` | Custom `<table>` in `ExecutionPanel` | Streamlit renders full interactive table; React shows first 3 rows with custom CSS styling |
| `st.code(sql, language="sql")` | `<pre><code className="text-green-200">` | Streamlit has syntax highlighting; React uses simple monospace font with green color |
| `st.spinner()` | `isLoading` state + animated dots | Streamlit's is automatic; React requires manual state management and custom UI |
| `st.button()` | `<Button>` or `<button onClick={...}>` | Streamlit triggers rerun on click; React calls function directly |
| `st.form()` + `st.form_submit_button()` | `<form onSubmit={handleSubmit}>` | Streamlit batches widget state until submit; React uses controlled inputs |
| `st.success()` / `st.error()` | `<Alert severity="success">` (MUI) | Streamlit's are built-in notifications; React uses Material-UI Alert component |
| `st.selectbox()` | `<select>` or MUI `Select` | Streamlit auto-updates session state; React needs `onChange` handler |
| `st.toggle()` / `st.checkbox()` | `<input type="checkbox">` or MUI `Switch` | Streamlit stores state automatically; React needs controlled component pattern |

### SQL execution result display

Execution results are rendered very differently between the two architectures:

**Streamlit** (`app_simple_gemini.py`):
- Results displayed in `st.expander("📊 Results")`
- Full dataframe rendered with `st.dataframe(result.data)`
- Metadata shown with `st.metric()` widgets
- SQL shown with `st.code(sql, language="sql")`
- Execute button triggers callback that updates message dict, then reruns to display

**React** (`ChatMessage.jsx:128-262 - ExecutionPanel component`):
- Results in custom `ExecutionPanel` component
- **Persistent SQL display** (lines 329-345): SQL card always visible, doesn't disappear after execution
- **Conditional Execute buttons** (lines 347-365): Only shown if SQL exists and not yet executed
- **ExecutionPanel** (lines 367-374): Only shown after execution completes
- Status indicators: Colored dots + text ("Executing...", "Valid", "150 rows", "Failed")
- First 3 rows preview in custom `<table>` with "... and N more rows" text
- Copy button for SQL
- Save button appears only after successful execution

**Key React pattern**:
```javascript
{/* SQL always visible */}
{extractedSql && <Card>SQL Query + Copy button</Card>}

{/* Execute buttons only if not executed */}
{extractedSql && !message.execution && <ExecuteButtons />}

{/* Results only if executed */}
{message.execution && <ExecutionPanel />}
```

This ensures SQL remains visible after execution, solving a common UX issue where the SQL would disappear when results load.

### Request lifecycles

1. **Structured query (`@create ...`)**
   1. `ChatInput` detects `@create`.
   2. `App.handleSend` builds payload with advanced options (mirrors Streamlit toggles) and calls `ragClient.runQuerySearch`.
   3. FastAPI `/query/search` returns `answer`, `sql`, `cleaned_sql`, metadata, and sources.
   4. UI displays answer, usage chips, sources, and SQL. Execution buttons go through `/sql/execute`.
   5. Saving results posts to `/saved_queries`, adding to the dashboard data set.

2. **Quick chat (no `@create`)**
   1. `App.handleSend` calls `ragClient.runQuickAnswer` with condensed settings.
   2. Backend `/query/quick` runs the same pipeline without SQL validation or advanced toggles.
   3. UI still tries to extract SQL client-side for convenience.

3. **SQL execution & dashboards**
   - `onExecute` in `ChatMessage` sends SQL (dry run or execute) to `/sql/execute` and renders results.
   - `onSave` sends results to `/saved_queries`.
   - `Dashboard` loads saved queries/dashboards, edits layout, and persists via `/dashboards` endpoints.

## 4. State Management: React vs Streamlit

Understanding how state works is key to navigating the React codebase if you're coming from Streamlit.

### Core state differences

| Aspect | Streamlit (`st.session_state`) | React (`useState`) |
| ------ | ------------------------------ | ------------------ |
| **Scope** | Server-side, persists across reruns | Client-side, lives in component memory |
| **Updates** | `st.session_state.key = value` triggers automatic rerun | `setState(newValue)` triggers component re-render |
| **Access** | Global dictionary accessible anywhere | Passed via props or managed in parent component |
| **Persistence** | Lasts entire session (until browser closes/refreshes) | Lost on page refresh (unless using localStorage) |
| **Update timing** | Synchronous, immediate | Asynchronous, React batches updates |

### Message structure comparison

**Streamlit message** (`app_simple_gemini.py`):
```python
{
    'role': 'user' | 'assistant',
    'content': str,  # Message text
    'timestamp': float,
    'sources': [Document],  # LangChain Document objects
    'usage': dict,  # {total_tokens, retrieval_time, ...}
    'extracted_sql': str,  # SQL from response
    'agent_type': str,  # 'create', 'explain', etc.
    'sql_execution_result': dict  # If executed
}
```

**React message** (`App.jsx`):
```javascript
{
  id: `${Date.now()}-user`,  // Unique identifier
  role: "user" | "assistant",
  content: str,  // Message text
  sql: str,  // Extracted/cleaned SQL (optional)
  rawAnswer: str,  // Original LLM response
  usage: {total_tokens, retrieval_time, generation_time, ...},
  sources: [{content, metadata}],
  execution: {  // Execution state (optional, added when Execute is clicked)
    status: "loading" | "success" | "error",
    result: {
      data: [{...}],  // Result rows
      columns: ["col1", "col2", ...],  // Column names
      row_count: 150,
      job_id: "...",
      bytes_processed: 12345,
      execution_time: 1.23
    },
    saving: "idle" | "pending",  // Save to dashboard state
    savedQueryId: str,  // ID after saving
    sql: str  // SQL that was executed
  },
  payload: {},  // Original API request
  question: str,  // User's original question
  mode: "concise"  // Chat mode indicator
}
```

The key difference: React's `execution` object tracks **UI state** (loading/success/error) separately from the result, allowing the UI to show loading spinners, error messages, and results independently.

### State update patterns

**Streamlit pattern** (reruns entire script):
```python
# User sends message
if prompt := st.chat_input("Ask..."):
    # Add to session state
    st.session_state.chat_messages.append({
        'role': 'user',
        'content': prompt
    })

    # Call RAG pipeline (blocks UI)
    answer, sources, usage = answer_question_chat_mode(...)

    # Add response to session state
    st.session_state.chat_messages.append({
        'role': 'assistant',
        'content': answer,
        'sources': sources
    })

    # Automatic rerun displays new messages
    st.rerun()
```

**React pattern** (updates specific state, re-renders components):
```javascript
// User sends message
const handleSend = async (question) => {
  // Add user message to conversation array
  const userMessage = {id: `${Date.now()}-user`, role: "user", content: question};
  setConversation(prev => [...prev, userMessage]);  // ← State update

  setIsLoading(true);  // ← Show loading indicator

  // Call API (non-blocking, async)
  const result = await runQuerySearch({question, ...});

  // Add assistant message to conversation array
  const assistantMessage = {
    id: `${Date.now()}-assistant`,
    role: "assistant",
    content: result.answer,
    sql: result.cleaned_sql,
    sources: result.sources
  };

  setConversation(prev => [...prev, assistantMessage]);  // ← State update
  setIsLoading(false);  // ← Hide loading indicator
};
```

React's pattern is **non-blocking**: the UI remains responsive during the API call. Streamlit blocks until the answer is ready.

### Execution state lifecycle

When a user clicks "Execute" on a SQL query:

**Streamlit:** Button click → rerun → execute query (blocks) → update message dict → rerun → display results in expander

**React:** Button click → update execution state to "loading" → re-render (shows spinner) → API call → update execution state to "success" + add result → re-render (shows table)

The React pattern allows showing intermediate states (loading spinner) and handling errors gracefully without blocking the entire UI.

### Conversation context serialization

Both architectures need to send conversation history to the LLM for context.

**Streamlit** (`app_simple_gemini.py:build_conversation_context`):
```python
def build_conversation_context():
    messages = st.session_state.chat_messages[-5:]  # Last 5 messages
    return "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in messages
    ])
```

**React** (`App.jsx:serializeHistory`):
```javascript
function serializeHistory(conversation) {
  return conversation.slice(-5).map(msg =>
    `${msg.role.toUpperCase()}: ${msg.content}`
  ).join("\n\n");
}
```

Both implementations send the last 5 messages as a string to the `/query/search` or `/query/quick` endpoint, which passes it to the LLM prompt.

## 5. Prompt Strategy & Model Selection

Prompt construction is centralized in the shared pipeline so Streamlit, FastAPI, and React all drive the LLM the same way.

### Agent-specific prompt templates

- **`simple_rag_simple_gemini.get_agent_prompt_template`** (`simple_rag_simple_gemini.py:429-534`) expands the core prompt according to `agent_type` and whether “Gemini mode” is enabled. It mirrors the Streamlit behavior:
  - `@create` → `"create"` agent: BigQuery-safe generation prompt, including data type reminders and fully qualified table requirements.
  - `@explain` → `"explain"` agent: Educational, step-by-step guidance.
  - `@longanswer` (Streamlit) → `"longanswer"` agent: Deep analysis with multiple examples; FastAPI defaults stay concise if no agent flag is present.
  - Default: two-to-three sentence answer prompt.
- The same helper is invoked inside `answer_question_simple_gemini`, regardless of caller (`app_simple_gemini.py`, `/query/search`, `/query/quick`).
- Conversation history, schema context, and retrieved examples are interpolated into the template before calling the LLM, matching the Streamlit `get_chat_prompt_template` flow (`app_simple_gemini.py:789-830`, `chat_system.py:22-146`).

### Prompt usage in the pipeline

1. **Frontend decides the agent.** `frontend/src/App.jsx:281-334` tags `@create` requests with `agent_type="create"` and leaves casual chat untagged. Streamlit’s `detect_chat_agent_type` performs the same parsing (`chat_system.py:22-47`).
2. **`run_query_search` forwards the hint.** `services/query_search_service.py:104-121` passes `agent_type`, `conversation_context`, and `llm_model` into `answer_question_simple_gemini`.
3. **Context assembly.** Inside `answer_question_simple_gemini` the schema manager, LookML safe joins, and retrieval results build a stitched context block before prompting (`simple_rag_simple_gemini.py:735-943`).
4. **Prompt logging and metrics.** The function logs prompt length, token estimates, and context utilization (for the Streamlit debug panel) so both backends inherit the same observability (`simple_rag_simple_gemini.py:945-985`, `simple_rag_simple_gemini.py:1080-1139`).

### Model routing

- **Defaults:** `answer_question_simple_gemini` uses `LLM_GEN_MODEL` env var or `"gemini-2.5-pro"` if not set (`simple_rag_simple_gemini.py:158-165`).
- **Overrides:** Both backend and Streamlit accept an optional `llm_model` argument; the React UI sets `"gemini-2.5-pro"` for structured prompts and `"gemini-2.5-flash"` for quick chat (`frontend/src/App.jsx:283-318`).
- **SQL extraction LLM:** When the backend needs to sanitize SQL it calls `services/sql_extraction_service.SQLExtractionService`, which spins up a lightweight Gemini client (`services/sql_extraction_service.py:23-89`). If the LLM isn’t available it falls back to regex patterns.
- **Specialized agents:** Streamlit’s `@schema` route diverts to `SchemaAgent` instead of the prompt pipeline (`chat_system.py:152-244`). FastAPI doesn’t expose that agent yet, but you can add it by propagating the flag through the API models.

## 5. Comparing to `app_simple_gemini.py`

| Concern | Streamlit implementation | FastAPI/React equivalent |
| ------- | ----------------------- | ------------------------ |
| UI events | Streamlit widgets and callbacks | React components (`ChatInput`, `ChatMessage`, `Dashboard`) |
| Question submission | Direct call to `run_query_search` inside Streamlit | `/query/search` and `/query/quick` endpoints; React sends payloads |
| SQL validation & execution | `run_sql_execution` and optional `validate_sql_safety` inside Streamlit | `/sql/execute` endpoint `→` `run_sql_execution` |
| Saved queries & dashboards | Streamlit pages reading/writing local JSON | FastAPI `/saved_queries` + `/dashboards`, React dashboard UI |
| Conversation history | Streamlit `conversation_manager` if available | React serializes messages and includes `conversation_context` in payload |
| Theming & layout | Streamlit theming | Custom CSS/JS in React |

The biggest difference is **where** the logic runs: Streamlit invokes the services inline, FastAPI exposes them as HTTP methods, and React drives the interactions. The actual pipeline code (`answer_question_simple_gemini`, vector store loading, SQL execution, prompt templates) remains identical.

## 6. Running the stack

```bash
# Backend (from rag_app/)
export VECTOR_STORE_NAME=index_sample_queries_with_metadata_recovered
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload

# Frontend (from rag_app/frontend/)
npm install        # first time
npm run dev -- --host 127.0.0.1 --port 5173
```

Set `VITE_API_BASE_URL` in `.env.local` to point the UI at a non-default backend URL if needed.

---

## 8. Appendix: Recent Architectural Decisions

This section documents important implementation choices made during the React frontend development to improve UX and maintain parity with the Streamlit app.

### A. Chat Message Centering (ChatGPT-style Layout)

**Problem:** Initial implementation had messages at extreme screen edges (user messages far right, assistant messages far left), creating poor visual balance on wide screens.

**Solution** (`ChatHistory.jsx:33`):
```javascript
<div style={{
  maxWidth: '56rem',      // ~896px centered column
  margin: '0 auto',       // Center horizontally
  padding: '0 2rem',      // 32px horizontal padding
  height: '100%',
  display: 'flex',
  flexDirection: 'column'
}}>
  <Stack spacing={2}>{/* messages */}</Stack>
</div>
```

Messages now align within a **centered column** instead of spanning full screen width, mimicking ChatGPT's layout. User messages align right within the column, assistant messages align left.

### B. Persistent SQL Display After Execution

**Problem:** Original implementation showed SQL before execution, but it would disappear when results loaded, making it hard to review the executed query.

**Solution** (`ChatMessage.jsx:329-375`):

Restructured component to show three **independent, conditional sections**:

1. **SQL Card** (always visible when SQL exists): Displays extracted SQL with Copy button
2. **Execute Buttons** (only if not executed): Execute and Dry Run buttons
3. **ExecutionPanel** (only if executed): Status, results table, metadata

**Before fix:**
```javascript
{extractedSql && !message.execution && (
  <div>
    <SQLCard />
    <ExecuteButtons />
  </div>
)}
{message.execution && <ExecutionPanel />}
```
Problem: SQL card hidden when execution starts.

**After fix:**
```javascript
{extractedSql && <SQLCard />}  {/* ← Always visible */}
{extractedSql && !message.execution && <ExecuteButtons />}
{message.execution && <ExecutionPanel />}
```

All three sections can coexist, ensuring SQL remains visible throughout the execution lifecycle.

### C. Backend Response Transformation

**Problem:** Backend `/sql/execute` returns flat structure with `total_rows` and `data` at top level, but UI components expect nested structure with `result.row_count`, `result.columns`, `result.data`.

**Solution** (`App.jsx:391-404`):

Frontend transforms response before storing in state:
```javascript
const transformedResult = {
  data: response.data || [],
  columns: response.data?.length > 0
    ? Object.keys(response.data[0])  // ← Extract column names
    : [],
  row_count: response.total_rows || 0,  // ← Rename field
  job_id: response.job_id,
  bytes_processed: response.bytes_processed,
  bytes_billed: response.bytes_billed,
  execution_time: response.execution_time,
  cache_hit: response.cache_hit,
  dry_run: response.dry_run,
};
```

**Benefits:**
- UI components don't need to know backend field names
- Column names automatically extracted from data (no backend changes needed)
- Consistent interface for `ExecutionPanel` component
- Maintains backward compatibility with backend API

### D. LLM-Based SQL Extraction on Backend

**Problem:** Client-side regex extraction (`utils/sqlExtractor.js`) worked for simple cases but failed with complex SQL wrapped in markdown, comments, or explanatory text.

**Solution** (`api/main.py:297-311`):

Backend `/query/search` endpoint now uses `SQLExtractionService` with Gemini Flash for reliable extraction:
```python
from services.sql_extraction_service import get_sql_extraction_service
sql_service = get_sql_extraction_service()
cleaned_sql = sql_service.extract_sql(
    result.answer_text,
    prefer_llm=True,  # Use Gemini for extraction
    debug=False
)
```

Returns both `sql` (original) and `cleaned_sql` (LLM-cleaned) in response. Frontend prefers `cleaned_sql`.

**Why LLM extraction:**
- Handles markdown code fences (`sql ... `)
- Removes explanatory comments
- Extracts SQL from complex multi-paragraph responses
- Same extraction logic used in Streamlit app

### E. Smart Auto-Scroll Behavior

**Problem:** Chat automatically scrolled to bottom on **every state update** (including execution status changes), interrupting users reading previous messages.

**Solution** (`ChatHistory.jsx:11-30`):

Implemented smart scrolling that only triggers when:
1. New message is added to conversation, AND
2. User is already near bottom (within 100px), OR
3. Last message is from assistant (new response)

```javascript
useEffect(() => {
  const previousLength = previousLengthRef.current;
  const hasNewMessage = conversation.length > previousLength;

  if (hasNewMessage && containerRef.current && bottomRef.current) {
    const container = containerRef.current;
    const isNearBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight < 100;

    const lastMessage = conversation[conversation.length - 1];
    const isAssistantMessage = lastMessage?.role === 'assistant';

    if (isNearBottom || isAssistantMessage) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }
  previousLengthRef.current = conversation.length;
}, [conversation]);
```

**Prevents:**
- Scroll interruption when execution results update
- Scroll interruption when user is reading older messages
- Scroll interruption on unrelated state changes

**Allows:**
- Scroll on new assistant responses
- Scroll if user is already at bottom (intended behavior)

### F. Dual SQL Extraction Strategy

**Architecture:** SQL extraction happens at **two levels**:

1. **Backend extraction** (`api/main.py:297-311`): LLM-based extraction using `services/sql_extraction_service.py`
   - More reliable
   - Handles complex cases
   - Returned as `cleaned_sql` field

2. **Frontend extraction** (`utils/sqlExtractor.js`): Regex-based fallback
   - Fast, no API call needed
   - Used when backend doesn't send `cleaned_sql`
   - Used for quick chat responses

**Preference order** (`App.jsx:297`):
```javascript
const sqlToStore = result.cleaned_sql || result.sql || extractSql(result.answer);
```

This ensures robust SQL extraction across all scenarios while minimizing unnecessary LLM calls.

---

With these architectural decisions documented, you can understand both **why** certain implementations exist and **how** they differ from the original Streamlit app. These patterns solve real UX issues discovered during user testing and migration from the Streamlit baseline.
