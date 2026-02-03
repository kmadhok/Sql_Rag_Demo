# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **SQL Retrieval-Augmented Generation (RAG) system** with a modern FastAPI backend and React frontend that enables natural language queries over SQL codebases using Google Gemini for generation, OpenAI embeddings, and FAISS vector stores. The application features a clean 2-tab interface (Chat + Dashboard) designed for portfolio presentation.

**Current Production Architecture (feature/2-tab-ui branch):**
- **Backend**: FastAPI service at `rag_app/api/main.py` exposing REST API endpoints
- **Frontend**: React 18 application at `rag_app/frontend/src/App.jsx` with 2-tab UI
- **Deployment**: Separate Google Cloud Run services (backend via buildpack, frontend via Docker)
- **Legacy Reference**: Streamlit app at `rag_app/app_simple_gemini.py` (preserved for reference, not used in production)

**Deployed Services:**
- Frontend: https://sql-rag-frontend-simple-481433773942.us-central1.run.app
- Backend API: https://sql-rag-api-simple-481433773942.us-central1.run.app
- API Docs: https://sql-rag-api-simple-481433773942.us-central1.run.app/docs

## Architecture

### System Architecture

**Frontend → Backend → RAG Pipeline → BigQuery**

```
React Frontend (2 tabs: Chat + Dashboard)
    ↓ HTTP/REST
FastAPI Backend (`api/main.py`)
    ↓ Service Layer
RAG Pipeline (retrieve → generate → execute)
    ↓ Query Execution
BigQuery (thelook_ecommerce dataset)
```

### Frontend Architecture (`rag_app/frontend/`)

**Technology Stack:**
- React 18 with functional components and hooks
- Vite for fast development and optimized builds
- Material-UI for component styling
- Recharts for data visualization
- Monaco Editor for SQL editing
- React Grid Layout for dashboard arrangement

**2-Tab UI Design:**
- **Chat Tab**: Natural language interface with conversation history, SQL generation, query execution
- **Dashboard Tab**: Saved queries, dashboard creation, data visualization with charts

**Key Frontend Components** (see FILE_INDEX.md for complete catalog):
- `App.jsx` - Main application with tab routing and state management (rag_app/frontend/src/App.jsx:66-69)
- `ChatHistory.jsx` - Conversation display with SQL results
- `Dashboard.jsx` - Dashboard management and visualization
- `Playground.jsx` - SQL editor (preserved, not currently in tabs)
- `DataOverview.jsx` - Query catalog browser (preserved, not currently in tabs)
- `Introduction.jsx` - Landing page (preserved, not currently in tabs)

**Component Communication:**
- API Client: `frontend/src/services/ragClient.js` - Centralized API calls to backend
- State Management: React hooks (`useState`, `useEffect`) and custom hooks in `frontend/src/hooks/`

### Backend Architecture (`rag_app/api/`)

**FastAPI Application** (`rag_app/api/main.py`)
- RESTful API with 30+ endpoints across multiple categories
- CORS enabled for frontend communication
- Health check endpoint at `/health`

**API Endpoint Categories:**
1. **Query & Generation**: `/query/search`, `/query/quick`, `/sql/execute`
2. **Data Management**: `/saved_queries` (CRUD operations)
3. **Dashboard**: `/dashboards` (create, list, update, delete)
4. **Schema Exploration**: `/schema/tables`, `/schema/tables/{table}/columns`, `/schema/tables/{table}/description`
5. **AI SQL Assistance**: `/sql/explain`, `/sql/complete`, `/sql/fix`, `/sql/format`, `/sql/chat`

**Service Layer** (`rag_app/services/`)
- `query_search_service.py` - RAG query processing orchestration
- `sql_execution_service.py` - SQL execution with validation
- `ai_assistant_service.py` - AI-powered SQL assistance
- `saved_query_service.py` - Saved queries CRUD
- `dashboard_service.py` - Dashboard management with Firestore
- `schema_service.py` - Schema exploration and AI descriptions
- `gemini_client.py` - Google Gemini LLM client wrapper

### Core RAG Pipeline Flow

1. **Embedding Generation** → Uses OpenAI `text-embedding-3-small` (default) or Ollama local models or Gemini embeddings
2. **Vector Store** → FAISS indices stored in `rag_app/faiss_indices/`
3. **Retrieval** → Hybrid search combining vector similarity (FAISS) and keyword matching (BM25)
4. **Generation** → Google Gemini models with 1M context window optimization
5. **Execution** → BigQuery SQL execution with safety validation

### Core RAG Components

**RAG Engine** (`rag_app/simple_rag_simple_gemini.py`)
- Core RAG implementation optimized for Gemini's large context window
- Smart deduplication using Jaccard similarity
- Context prioritization and token optimization

**LLM Registry** (`rag_app/llm_registry.py`)
- Centralizes model selection per pipeline role
- Environment variables: `LLM_PARSE_MODEL`, `LLM_GEN_MODEL`, `LLM_REWRITE_MODEL`, `LLM_CHAT_MODEL`
- Defaults: `gemini-2.5-pro` for generation, `gemini-2.5-flash-lite` for parsing/chat

**Chat System** (`rag_app/chat_system.py`)
- Specialized agents: `@explain`, `@create`, `@longanswer`, `@schema`
- Default behavior: concise responses (2-3 sentences)
- Multi-turn conversation support

**Schema Management** (`rag_app/schema_manager.py`)
- Smart schema injection based on retrieved queries
- Table join analysis and relationship mapping
- Schema CSV: `rag_app/schema.csv` or `rag_app/data_new/thelook_ecommerce_schema.csv`

**BigQuery Integration** (`rag_app/core/bigquery_executor.py`)
- Secure read-only SQL execution against `thelook_ecommerce` dataset
- Safety validation, cost estimation, dry-run support
- Result caching and performance metrics

**SQL Validation** (`rag_app/core/sql_validator.py`)
- Multi-level validation (strict/basic)
- Safety checks blocking DELETE, DROP, UPDATE, etc.
- Table/column name validation against schema

**Conversation Manager** (`rag_app/core/conversation_manager.py`)
- Persistent conversation storage via Google Firestore
- Message history and context management

**Hybrid Search** (`rag_app/hybrid_retriever.py`)
- Combines FAISS vector similarity + BM25 keyword matching
- Configurable search weights via `SearchWeights` dataclass

**Query Rewriting** (`rag_app/query_rewriter.py`)
- Transforms user queries for better retrieval
- LLM-based query expansion and refinement

## Development Commands

### Setup & Installation
```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
pip install -r rag_app/requirements.txt

# Install test dependencies
pip install -r requirements-test.txt

# Install frontend dependencies
cd rag_app/frontend
npm install
cd ..

# Set up environment variables (required)
export OPENAI_API_KEY=sk-your-openai-api-key
export GEMINI_API_KEY=your-gemini-api-key

# Optional: Configure LLM models
export LLM_GEN_MODEL="gemini-2.5-pro"
export LLM_PARSE_MODEL="gemini-2.5-flash-lite"

# Optional: Configure embedding provider
export EMBEDDINGS_PROVIDER=gemini  # or openai or ollama
```

### Embedding Generation
```bash
# Generate vector embeddings (required before first run)
cd rag_app
python standalone_embedding_generator.py --csv "sample_queries_with_metadata.csv"

# Generate analytics cache for Query Catalog
python catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv"

# Alternative: Use local Ollama embeddings
export EMBEDDINGS_PROVIDER=ollama
python standalone_embedding_generator.py --csv "sample_queries_with_metadata.csv"
```

### Running the Application (Development)

**Option 1: Backend + Frontend Separately (Recommended for Development)**
```bash
# Terminal 1: Start FastAPI backend
cd rag_app
python -m uvicorn api.main:app --reload --port 8080

# Backend runs at http://localhost:8080
# API docs at http://localhost:8080/docs

# Terminal 2: Start React frontend
cd rag_app/frontend
npm run dev

# Frontend runs at http://localhost:3000 (or 3003 if port conflicts)
```

**Option 2: Legacy Streamlit Interface (Reference Only)**
```bash
# Start legacy Streamlit application (not used in production)
cd rag_app
streamlit run app_simple_gemini.py

# Access at http://localhost:8501
```

### Testing
```bash
# Run all tests from project root
pytest

# Run with verbose output
pytest -v

# Run specific test categories
pytest -m chat        # Chat tests only
pytest -m sql         # SQL tests only
pytest -m catalog     # Catalog tests only
pytest -m agent       # Agent tests only

# Run unit tests only (fast, uses mocks)
pytest tests/e2e/

# Run integration tests only (slow, requires API keys)
pytest -m integration

# Run with coverage
pytest --cov=rag_app --cov-report=term-missing

# Run specific test file
pytest tests/e2e/test_chat_conversation_flow.py

# Run single test
pytest tests/e2e/test_chat_conversation_flow.py::TestChatConversationFlow::test_simple_question_answer_flow
```

### Integration Testing
```bash
# FIRST: Set up test vector store (one-time setup)
export OPENAI_API_KEY=your-key
python tests/integration/setup_test_vector_store.py

# Run all integration tests
pytest tests/integration/ -v -m integration

# Run specific integration test
pytest tests/integration/test_complete_pipeline.py::TestCompleteRAGPipeline::test_simple_product_query -v

# Required environment variables for integration tests:
export OPENAI_API_KEY=your-openai-key       # For embeddings
export GEMINI_API_KEY=your-gemini-key       # For SQL generation
export GOOGLE_APPLICATION_CREDENTIALS=path  # For BigQuery (or use gcloud auth)
```

### Batch Query Processing
```bash
# Run batch questions through Query Search pipeline
cd rag_app
python scripts/run_batch_questions.py \
  --questions-file scripts/questions.example.txt \
  --output-dir logs/batch_run \
  --index-name index_transformed_sample_queries

# Options:
# --no-execute: Skip BigQuery execution
# --basic-validation: Relax schema checks
```

### Tools & Utilities
```bash
# Sample two tables for testing
cd rag_app
python tools/sample_two_tables.py
```

## Deployment

### Google Cloud Run Deployment

**See comprehensive documentation:**
- **DEPLOYMENT.md** - Complete deployment guide (19 KB, step-by-step instructions)
- **QUICKSTART.md** - Minimal quick-start guide (3 KB, for experienced users)

**Quick Deployment:**
```bash
cd rag_app

# Option 1: Deploy everything at once (~13 minutes)
./deploy_all.sh

# Option 2: Deploy separately
./deploy_api_simple.sh              # Backend (~5 min, buildpack mode)
cd frontend
./deploy_frontend_simple.sh         # Frontend (~8 min, Docker mode)
```

**Prerequisites Check:**
```bash
cd rag_app
./preflight_check.sh  # Validates Docker, gcloud auth, .env.deploy, FAISS indices, etc.
```

**Deployment Scripts Overview:**

Current scripts (use these):
- `deploy_all.sh` - One-command deployment (backend + frontend)
- `deploy_api_simple.sh` - Backend only (buildpack mode)
- `frontend/deploy_frontend_simple.sh` - Frontend only (Docker mode)
- `preflight_check.sh` - Prerequisites validation

Deprecated scripts (do not use):
- `deploy.sh`, `deploy_api_frontend.sh`, `deploy_cloudbuild.sh`

**Environment Configuration:**
```bash
# Create deployment environment file
cp .env.deploy.example .env.deploy
# Edit .env.deploy and add your API keys:
# - GEMINI_API_KEY
# - OPENAI_API_KEY
# - EMBEDDINGS_PROVIDER
```

**Deployment Architecture:**
- **Backend**: Deployed via Cloud Buildpacks (auto-detects Python/FastAPI from `Procfile`)
- **Frontend**: Deployed via Docker (multi-stage build: Node.js → Nginx)
- **Services**: `sql-rag-api-simple` (backend), `sql-rag-frontend-simple` (frontend)
- **Region**: us-central1
- **Project**: brainrot-453319

**Monitoring:**
```bash
# Backend logs
gcloud run services logs read sql-rag-api-simple --region us-central1

# Frontend logs
gcloud run services logs read sql-rag-frontend-simple --region us-central1

# Backend health check
curl https://sql-rag-api-simple-481433773942.us-central1.run.app/health
```

## Important Implementation Details

### Python Version
- Uses `pyenv` for version management
- Create `.python-version` file with version (e.g., `3.12.0`)
- Run `pyenv local 3.12.0` to set local Python version

### Environment Configuration
Key files:
- `rag_app/config.py` - Central configuration constants
- `rag_app/.env` (not tracked) - API keys and secrets for local development
- `rag_app/.env.deploy` (not tracked) - API keys for deployment (created from `.env.deploy.example`)
- `.python-version` (not tracked) - Local Python version

### Data Files
- **CSV Source**: `rag_app/sample_queries_with_metadata.csv`
- **Schema**: `rag_app/schema.csv` or `rag_app/data_new/thelook_ecommerce_schema.csv`
- **FAISS Indices**: `rag_app/faiss_indices/` (generated, not tracked)
- **Analytics Cache**: `rag_app/catalog_analytics/` (JSON files)
- **LLM Cache**: `rag_app/llm_sql_cache/` (query response caching)

### BigQuery Integration
- **Project ID**: Configurable via `BIGQUERY_PROJECT_ID` env var (default: `brainrot-453319`)
- **Dataset**: `bigquery-public-data.thelook_ecommerce` (default)
- **Authentication**: Uses Application Default Credentials (run `gcloud auth application-default login`)
- **Safety**: Read-only queries enforced, no DML/DDL allowed

### Chat Agents
The Chat interface supports specialized agents via `@` prefix:
- **@explain** - Detailed explanations of SQL concepts
- **@create** - SQL query generation
- **@longanswer** - Comprehensive detailed responses
- **@schema** - Schema exploration and table information
- **Default (no @)** - Concise 2-3 sentence responses

### Vector Store Management
Vector stores are loaded from `rag_app/faiss_indices/`:
- Naming convention: `index_<source_name>`
- Contains both FAISS index and metadata
- Regenerate after updating source CSV

### Hybrid Search Configuration
Adjust search weights in UI or programmatically:
```python
from hybrid_retriever import SearchWeights
weights = SearchWeights(vector=0.7, keyword=0.3)
```

### SQL Validation Levels
Two validation modes in `ValidationLevel` enum:
- **STRICT** - Full table/column validation against schema
- **BASIC** - Safety checks only (no schema validation)

## Testing Architecture

The test suite consists of TWO distinct testing strategies:

### 1. Unit Tests (`tests/e2e/`)
**Purpose**: Fast feedback during development, tests code logic with mocked dependencies

**Characteristics**:
- Uses mock components (MockVectorStore, MockGeminiClient, MockBigQueryExecutor)
- No API keys required
- Runs in seconds
- Tests code paths, error handling, and business logic
- Does NOT validate actual LLM output quality or real API behavior

**Test Structure**:
```
tests/
├── fixtures/          # Mock data and helpers
│   ├── mock_helpers.py
│   └── sample_test_queries.csv
└── e2e/              # Unit tests with mocked components
    ├── conftest.py   # Mock fixtures
    ├── test_chat_conversation_flow.py
    ├── test_sql_generation_and_execution.py
    ├── test_catalog_browsing_flow.py
    └── test_agent_workflows.py
```

**Key Mock Fixtures** (in `tests/e2e/conftest.py`):
- `mock_vector_store` - Mocked FAISS vector store
- `mock_gemini_client` - Mocked LLM client
- `mock_bigquery_executor` - Mocked BigQuery executor
- `mock_schema_manager` - Mocked schema manager
- `mock_conversation_manager` - Mocked conversation storage

### 2. Integration Tests (`tests/integration/`)
**Purpose**: Validate complete pipeline with real components (NO MOCKS)

**Characteristics**:
- Uses REAL OpenAI embeddings
- Uses REAL FAISS vector stores
- Uses REAL Gemini API
- Uses REAL BigQuery execution (read-only)
- Requires API keys and credentials
- Runs in minutes (due to API calls)
- Validates actual user experience end-to-end

**Test Structure**:
```
tests/integration/
├── conftest.py                    # Real component fixtures
├── test_complete_pipeline.py      # Complete RAG pipeline tests
├── test_questions.yaml            # Predefined test questions
├── setup_test_vector_store.py     # One-time setup script
└── test_vector_store/             # Generated by setup script
    ├── index.faiss
    └── index.pkl
```

**Key Real Fixtures** (in `tests/integration/conftest.py`):
- `vector_store` - Real FAISS vector store loaded from disk
- `gemini_client` - Real Gemini API client
- `bigquery_client` - Real BigQuery client
- `schema_manager` - Real schema manager with actual schema data
- `embedding_function` - Real OpenAI embedding function

**Setup Process**:
1. Run `python tests/integration/setup_test_vector_store.py` to generate test vector store
2. Set environment variables: `OPENAI_API_KEY`, `GEMINI_API_KEY`, BigQuery credentials
3. Run tests: `pytest tests/integration/ -v -m integration`

**What Integration Tests Validate**:
- Embedding generation quality
- Vector retrieval relevance
- Gemini SQL generation correctness
- BigQuery execution success
- Complete pipeline response time
- Agent workflows (@explain, @create, @schema)
- SQL safety validation
- Conversation context handling

### Test Markers
Configure test execution with pytest markers:
- `@pytest.mark.integration` - True integration tests (real APIs, no mocks)
- `@pytest.mark.e2e` - Unit tests with mocked components
- `@pytest.mark.chat` - Chat functionality
- `@pytest.mark.sql` - SQL generation/execution
- `@pytest.mark.catalog` - Catalog browsing
- `@pytest.mark.agent` - Agent workflows
- `@pytest.mark.slow` - Long-running tests

### When to Run Which Tests

**During Development** (fast feedback loop):
```bash
pytest tests/e2e/  # Unit tests only, ~10-30 seconds
```

**Before Committing** (validate logic):
```bash
pytest tests/e2e/ -v  # All unit tests with details
```

**Before Releasing** (validate complete system):
```bash
pytest tests/integration/ -v -m integration  # Full integration tests, ~5-10 minutes
```

**CI/CD Pipeline**:
- Always run unit tests
- Run integration tests on main branch or before releases
- Integration tests require secrets management for API keys

## Common Patterns

### Adding New Data Source
1. Prepare CSV with columns: `query`, `description`, `tables_used`, `joins_used`
2. Run embedding generation: `python standalone_embedding_generator.py --csv "new_data.csv"`
3. Update `config.py` if needed to point to new CSV path
4. Restart application

### Adding New LLM Provider
1. Create client in `rag_app/<provider>_client.py` following `gemini_client.py` pattern
2. Update `llm_registry.py` to support new provider
3. Add environment variable configuration

### Modifying Chat Agents
1. Update agent detection in `chat_system.py::detect_chat_agent_type()`
2. Add prompt template in `chat_system.py::get_chat_prompt_template()`
3. Update UI indicators in `chat_system.py::get_chat_agent_indicator()`

### Extending SQL Validation
1. Modify validation logic in `core/sql_validator.py`
2. Update `ValidationLevel` enum if adding new levels
3. Add corresponding tests in `tests/e2e/test_sql_generation_and_execution.py`

### Adding New API Endpoint
1. Add endpoint in `api/main.py`
2. Create service in `services/` if logic is complex
3. Update `frontend/src/services/ragClient.js` to call new endpoint
4. Add tests in `tests/e2e/`

### Adding New React Component
1. Create component in `frontend/src/components/`
2. Import in parent component or `App.jsx`
3. Update styling in component or `frontend/src/styles.css`
4. See FILE_INDEX.md for component organization

### Adding New Tab to UI
1. Update tabs array in `frontend/src/App.jsx` (rag_app/frontend/src/App.jsx:66-69)
2. Add TabPanel in JSX with new tab content
3. Create or import component for tab content
4. Update default tab if needed

## Configuration Files

**Backend:**
- `pytest.ini` - Test configuration and markers
- `requirements-test.txt` - Test dependencies only
- `rag_app/requirements.txt` - Production dependencies (FastAPI, no Streamlit)
- `rag_app/requirements_legacy.txt` - Legacy dependencies with Streamlit
- `rag_app/Procfile` - Buildpack entry point for Cloud Run

**Frontend:**
- `rag_app/frontend/package.json` - Node.js dependencies and npm scripts
- `rag_app/frontend/vite.config.js` - Vite build configuration (dev server port 3000, proxy)
- `rag_app/frontend/tsconfig.json` - TypeScript configuration
- `rag_app/frontend/eslint.config.js` - ESLint linting rules
- `rag_app/frontend/.env` - Frontend environment (VITE_API_BASE_URL)

**Deployment:**
- `rag_app/.env.deploy.example` - Deployment environment template
- `rag_app/.gcloudignore` - Files to exclude from Cloud Run uploads
- `rag_app/frontend/Dockerfile` - Frontend Docker multi-stage build
- `rag_app/frontend/nginx.conf` - Nginx configuration for SPA routing

## Documentation Files

**See FILE_INDEX.md for complete file catalog** (433 lines cataloging all 110+ files)

**Key Documentation:**
- `FILE_INDEX.md` - Complete file catalog with purposes and descriptions (root)
- `DEPLOYMENT.md` - Comprehensive deployment guide (rag_app/)
- `QUICKSTART.md` - Minimal deployment quick-start (rag_app/)
- `README.md` - Project overview and setup instructions (root)
- `CLAUDE.md` - This file - developer guide for Claude Code (root)
- `tests/README.md` - Testing documentation

## Token Cost Tracking

Token costs are defined in `config.py::TOKEN_COSTS`:
- Gemini 2.5 Flash Lite: $0.000075 input / $0.0003 output (per 1K tokens)
- Gemini 2.5 Pro: Configurable in registry
- Application tracks and displays token usage per query

## Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Debug logs for SQL validation pipeline are written to `rag_app/debug_logs.md`.

## Important Notes

- **Context Window**: Optimized for Gemini's 1M token context (stays under 800K with buffer)
- **Caching**: Multiple cache layers - embeddings, LLM responses, BigQuery results, analytics
- **Windows Compatibility**: No complex async processors; uses standalone embedding generator
- **Firestore**: Conversation persistence requires Google Cloud Firestore setup
- **Schema CSV Format**: Must have `table_id`, `column`, `datatype` columns
- **Current Branch**: feature/2-tab-ui (simplified from 5 tabs to 2 for portfolio focus)
- **Legacy Streamlit App**: `app_simple_gemini.py` preserved as reference, not used in production deployment
