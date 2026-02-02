# SQL RAG Application - File Index

**Complete catalog of all files in the SQL RAG codebase with purposes and descriptions.**

Use this index to quickly understand what each file does and where to find specific functionality.

---

## Table of Contents

1. [Backend Application Files](#backend-application-files)
2. [API Layer](#api-layer)
3. [Core Modules](#core-modules)
4. [Services](#services)
5. [RAG Pipeline Components](#rag-pipeline-components)
6. [Frontend Application](#frontend-application)
7. [Frontend Components](#frontend-components)
8. [Frontend Services & Utils](#frontend-services--utils)
9. [Data Files](#data-files)
10. [Scripts & Tools](#scripts--tools)
11. [Documentation](#documentation)
12. [Configuration Files](#configuration-files)

---

## Backend Application Files

**Location:** `rag_app/`

| File | Purpose | Key Features |
|------|---------|--------------|
| **app_simple_gemini.py** | Main Streamlit application (legacy UI) | Multi-page app with Query Search, Chat, and Catalog modes |
| **config.py** | Central configuration constants | Index names, model settings, token costs, paths |
| **simple_rag_simple_gemini.py** | Core RAG implementation optimized for Gemini's 1M context window | Smart deduplication, context prioritization, token optimization |
| **llm_registry.py** | Centralized LLM model selection per pipeline role | Environment-based model configuration for parse/gen/rewrite/chat |
| **chat_system.py** | Chat agents and specialized response modes | @explain, @create, @longanswer, @schema agents |
| **schema_manager.py** | Smart schema injection based on retrieved queries | Table join analysis, relationship mapping from schema CSV |
| **query_rewriter.py** | LLM-based query transformation for better retrieval | Query expansion and refinement |
| **hybrid_retriever.py** | Combines FAISS vector similarity + BM25 keyword matching | Configurable search weights via SearchWeights dataclass |
| **standalone_embedding_generator.py** | Generates FAISS vector embeddings from CSV | Windows-compatible, OpenAI or Ollama embeddings |
| **catalog_analytics_generator.py** | Pre-computes analytics for Query Catalog | Generates JSON cache for faster catalog browsing |

---

## API Layer

**Location:** `rag_app/api/`

| File | Purpose | Endpoints Provided |
|------|---------|-------------------|
| **main.py** | FastAPI entry point exposing the Query Search LLM pipeline | `/query/search`, `/query/quick`, `/sql/execute`, `/saved_queries`, `/dashboards`, `/schema/*`, `/sql/*` |
| **health.py** | Health check endpoint | `/health` - Returns service status |

### API Endpoint Categories

**Query & Generation:**
- `POST /query/search` - RAG-based SQL generation
- `POST /query/quick` - Quick concise answers
- `POST /sql/execute` - Execute SQL on BigQuery

**Data Management:**
- `POST /saved_queries` - Save query results
- `GET /saved_queries` - List saved queries
- `GET /saved_queries/{id}` - Get specific query

**Dashboard:**
- `POST /dashboards` - Create dashboard
- `GET /dashboards` - List dashboards
- `PATCH /dashboards/{id}` - Update dashboard
- `DELETE /dashboards/{id}` - Delete dashboard

**Schema Exploration:**
- `GET /schema/tables` - List all tables
- `GET /schema/tables/{table}/columns` - Get columns
- `GET /schema/tables/{table}/description` - AI description

**AI SQL Assistance:**
- `POST /sql/explain` - Explain SQL
- `POST /sql/complete` - Autocomplete
- `POST /sql/fix` - Debug/fix SQL
- `POST /sql/format` - Format SQL
- `POST /sql/chat` - Conversational assistance

---

## Core Modules

**Location:** `rag_app/core/`

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| **bigquery_executor.py** | Secure read-only SQL execution against BigQuery | `BigQueryExecutor` - Execute queries with safety validation, cost estimation, dry-run support |
| **sql_validator.py** | Multi-level SQL safety validation | `SafeSQLValidator` - Validates SQL for safety (blocks DELETE/DROP/UPDATE), table/column validation |
| **conversation_manager.py** | Persistent conversation storage via Google Firestore | `ConversationManager` - Store and retrieve chat history |
| **sql_cache.py** | Caching layer for SQL query results | In-memory and disk-based caching for performance |

---

## Services

**Location:** `rag_app/services/`

| File | Purpose | Used By |
|------|---------|---------|
| **query_search_service.py** | RAG query processing orchestration | `api/main.py` - Handles /query/search endpoint |
| **sql_execution_service.py** | SQL execution orchestration with validation | `api/main.py` - Handles /sql/execute endpoint |
| **ai_assistant_service.py** | AI-powered SQL assistance (explain, fix, complete, chat) | `api/main.py` - Powers /sql/* endpoints |
| **saved_query_service.py** | Saved queries CRUD operations | `api/main.py` - Manages saved queries |
| **dashboard_service.py** | Dashboard management with Firestore persistence | `api/main.py` - Handles /dashboards endpoints |
| **schema_service.py** | Schema exploration and AI descriptions | `api/main.py` - Powers /schema/* endpoints |
| **conversation_service.py** | Conversation management and persistence | Chat endpoints |
| **gemini_client.py** | Google Gemini LLM client wrapper | All LLM operations (generation, parsing, chat) |

---

## RAG Pipeline Components

**Location:** `rag_app/`

| File | Purpose | Pipeline Stage |
|------|---------|----------------|
| **embedding_provider.py** | Unified embedding interface (OpenAI, Ollama, Gemini) | Embedding Generation |
| **vector_store.py** | FAISS vector store loading and search | Retrieval |
| **simple_rag_simple_gemini.py** | Context assembly and LLM prompting | Generation |
| **hybrid_retriever.py** | Hybrid vector + keyword search | Retrieval Enhancement |
| **query_rewriter.py** | Query transformation for better retrieval | Pre-Retrieval |
| **schema_manager.py** | Schema injection based on context | Post-Retrieval / Pre-Generation |

---

## Frontend Application

**Location:** `rag_app/frontend/`

### Main Application Files

| File | Purpose |
|------|---------|
| **src/main.jsx** | React application entry point, renders App component |
| **src/App.jsx** | Main app component with 2-tab UI (Chat + Dashboard), routing, state management |
| **src/index.css** | Global styles and CSS variables |
| **src/styles.css** | Component-specific styles |

### Configuration Files

| File | Purpose |
|------|---------|
| **vite.config.js** | Vite build configuration (dev server port 3000, proxy settings) |
| **package.json** | Dependencies and npm scripts (dev, build, preview) |
| **tsconfig.json** | TypeScript configuration |
| **eslint.config.js** | ESLint linting rules |
| **.env** | Environment variables (VITE_API_BASE_URL) |
| **Dockerfile** | Multi-stage Docker build (Node.js → Nginx) |
| **nginx.conf** | Nginx configuration for SPA routing |

---

## Frontend Components

**Location:** `rag_app/frontend/src/components/`

### Core UI Components

| Component | Purpose | Props |
|-----------|---------|-------|
| **ChatHistory.jsx** | Displays conversation messages with SQL results | `conversation`, `error`, `onExecute`, `onSave` |
| **ChatMessage.jsx** | Individual message bubble with SQL code highlighting | `message`, `onExecute`, `onSave` |
| **ChatInput.jsx** | User input form with options panel | `onSend`, `isLoading`, `options`, `onOptionsChange` |
| **Introduction.jsx** | Landing page with feature showcase | None |
| **Dashboard.jsx** | Dashboard management and visualization | `savedQueries`, `currentDashboard`, `onSaveDashboard`, `dashboards`, `onSelectDashboard`, `onCreateDashboard` |
| **DataOverview.jsx** | Browse saved queries and catalog | `savedQueries`, `onRefresh` |
| **Playground.jsx** | SQL editor with execution and visualization | None (self-contained) |

### Utility Components

| Component | Purpose |
|-----------|---------|
| **Button.jsx** | Reusable button with variants (primary, secondary, danger) |
| **ThemeToggle.jsx** | Dark/light mode switcher |
| **TemplatePickerModal.jsx** | Modal for selecting dashboard templates |
| **ErrorDisplay.jsx** | Error message display component |
| **LoadingSpinner.jsx** | Loading indicator |

### Dashboard Components

| Component | Purpose |
|-----------|---------|
| **DashboardGrid.jsx** | React Grid Layout wrapper for dashboard items |
| **ChartCard.jsx** | Individual chart/widget card with title, actions |
| **ChartRenderer.jsx** | Renders different chart types (bar, line, pie, table) |
| **SavedQueryCard.jsx** | Card showing saved query with preview |
| **DashboardSelector.jsx** | Dropdown to switch between dashboards |

### Data Visualization Components

| Component | Purpose |
|-----------|---------|
| **BarChart.jsx** | Bar chart using Recharts |
| **LineChart.jsx** | Line chart using Recharts |
| **PieChart.jsx** | Pie chart using Recharts |
| **DataTable.jsx** | Tabular data display with pagination |
| **QueryResultsTable.jsx** | SQL query results table |

### SQL Editor Components

| Component | Purpose |
|-----------|---------|
| **MonacoEditor.jsx** | SQL code editor with syntax highlighting (Monaco Editor) |
| **SqlFormatter.jsx** | SQL formatting utility button |
| **QueryExecutor.jsx** | Execute SQL with dry-run option |

### Form Components

| Component | Purpose |
|-----------|---------|
| **OptionsPanel.jsx** | Advanced options for query search (k, weights, validation) |
| **SearchWeightsSlider.jsx** | Adjust vector/keyword search balance |
| **ModelSelector.jsx** | Choose LLM model |

---

## Frontend Services & Utils

**Location:** `rag_app/frontend/src/`

### Services

| File | Purpose |
|------|---------|
| **services/ragClient.js** | API client for all backend endpoints (query, execute, save, dashboards, schema) |
| **services/apiClient.js** | Base HTTP client with error handling |

### Utilities

| File | Purpose |
|------|---------|
| **utils/sqlExtractor.js** | Extract SQL code from markdown/text responses |
| **utils/sqlFormatter.js** | Format SQL code for display |
| **utils/dashboardTemplates.js** | Predefined dashboard layouts |
| **utils/themes.js** | Theme management (dark/light mode) |
| **utils/chartUtils.js** | Chart data transformation helpers |
| **utils/dateUtils.js** | Date formatting utilities |
| **utils/storageUtils.js** | Local storage helpers |

### Hooks

| File | Purpose |
|------|---------|
| **hooks/useLocalStorage.js** | React hook for localStorage persistence |
| **hooks/useDashboard.js** | Dashboard state management |
| **hooks/useQueryExecution.js** | SQL execution state management |

### Types

| File | Purpose |
|------|---------|
| **types/index.ts** | TypeScript type definitions for API responses, components |

---

## Data Files

**Location:** `rag_app/`

### CSV Files

| File | Purpose | Columns |
|------|---------|---------|
| **sample_queries_with_metadata.csv** | Source queries for RAG retrieval | query, description, tables_used, joins_used |
| **schema.csv** or **data_new/thelook_ecommerce_schema.csv** | Database schema definition | table_id, column, datatype, description |

### JSON Files

| File | Purpose |
|------|---------|
| **lookml_safe_join_map.json** | LookML explore definitions for safe table joins |
| **catalog_analytics/*.json** | Pre-computed analytics cache for Query Catalog |
| **llm_sql_cache/*.json** | Cached LLM responses for query optimization |

### FAISS Indices

| Directory | Purpose |
|-----------|---------|
| **faiss_indices/index_sample_queries_with_metadata_recovered/** | FAISS vector embeddings (index.faiss, index.pkl) |

---

## Scripts & Tools

**Location:** `rag_app/`

### Deployment Scripts

| Script | Purpose | Use When |
|--------|---------|----------|
| **deploy_all.sh** | Deploy backend + frontend to Cloud Run | Complete deployment |
| **deploy_api_simple.sh** | Deploy backend (buildpack mode) | Backend updates |
| **frontend/deploy_frontend_simple.sh** | Deploy frontend (Docker mode) | Frontend updates |
| **preflight_check.sh** | Validate prerequisites before deployment | Before any deployment |
| **deploy.sh** | ⚠️ DEPRECATED - Use deploy_all.sh | N/A |
| **deploy_api_frontend.sh** | ⚠️ DEPRECATED - Use deploy_all.sh | N/A |
| **deploy_cloudbuild.sh** | ⚠️ DEPRECATED - Use deploy_api_simple.sh | N/A |

### Utility Scripts

| Script | Purpose |
|--------|---------|
| **scripts/run_batch_questions.py** | Run batch queries through RAG pipeline for testing |
| **tools/sample_two_tables.py** | Sample data from BigQuery tables for testing |

### Data Generation Scripts

| Script | Purpose |
|--------|---------|
| **standalone_embedding_generator.py** | Generate FAISS embeddings from CSV |
| **catalog_analytics_generator.py** | Generate analytics cache for catalog |

---

## Documentation

**Location:** `rag_app/` and root

### Deployment Documentation

| File | Purpose |
|------|---------|
| **DEPLOYMENT.md** | Comprehensive deployment guide (prerequisites, step-by-step, troubleshooting) |
| **QUICKSTART.md** | Minimal quick-start deployment guide |
| **.env.deploy.example** | Environment variable template with API key placeholders |

### Project Documentation

| File | Purpose |
|------|---------|
| **README.md** | Main project documentation (overview, features, architecture, setup) |
| **frontend/README.md** | Frontend-specific documentation (setup, development) |
| **tests/README.md** | Testing documentation (structure, how to run tests) |
| **CLAUDE.md** | Comprehensive developer guide (architecture, commands, testing, deployment) |
| **FILE_INDEX.md** | This file - complete file catalog |

### Migration Documentation

| File | Purpose |
|------|---------|
| **STREAMLIT_TO_FASTAPI_REACT_MIGRATION_COMPLETION.md** | Feature migration matrix |
| **STREAMLIT_TO_FASTAPI_REACT_MIGRATION_ROADMAP.md** | Migration planning |
| **README_REFACTORING.md** | Refactoring safety procedures |
| **README_GEMINI_MIGRATION.md** | Gemini LLM migration details |
| **README_DESCRIPTIONS.md** | Description generation system |
| **docs/IMPLEMENTATION_STATUS.md** | Refactoring progress tracking |
| **docs/IMPLEMENTATION_SUMMARY.md** | Embedding processor implementation |

---

## Configuration Files

**Location:** `rag_app/`

### Backend Configuration

| File | Purpose |
|------|---------|
| **.env** | Environment variables (API keys, project IDs) |
| **.env.deploy** | Deployment environment (git-ignored) |
| **.env.deploy.example** | Template for .env.deploy |
| **config.py** | Python configuration constants |
| **.python-version** | Python version for pyenv |
| **requirements.txt** | Python dependencies (API service only, no Streamlit) |
| **requirements_legacy.txt** | Legacy dependencies with Streamlit |
| **pytest.ini** | Pytest configuration and test markers |
| **Procfile** | Buildpack entry point: `web: uvicorn api.main:app --host 0.0.0.0 --port $PORT` |

### Frontend Configuration

| File | Purpose |
|------|---------|
| **frontend/.env** | Frontend environment (VITE_API_BASE_URL) |
| **frontend/package.json** | Node.js dependencies and scripts |
| **frontend/vite.config.js** | Vite build configuration |
| **frontend/tsconfig.json** | TypeScript configuration |
| **frontend/eslint.config.js** | ESLint rules |

### Cloud Configuration

| File | Purpose |
|------|---------|
| **.gcloudignore** | Files to exclude from Cloud Run uploads |
| **Dockerfile.api** | Backend Docker build (not used in simple deployment) |
| **frontend/Dockerfile** | Frontend multi-stage Docker build |
| **frontend/nginx.conf** | Nginx configuration for SPA routing |
| **docker-compose.yml** | Local multi-service Docker setup |

---

## Quick Reference: Common Tasks → Files to Edit

| Task | Files to Modify |
|------|----------------|
| **Add new API endpoint** | `api/main.py`, create service in `services/` |
| **Change RAG logic** | `simple_rag_simple_gemini.py` |
| **Modify SQL validation** | `core/sql_validator.py` |
| **Add new chat agent** | `chat_system.py` (detect_chat_agent_type, get_chat_prompt_template) |
| **Change embedding provider** | `embedding_provider.py`, regenerate FAISS indices |
| **Add frontend component** | Create in `frontend/src/components/`, import in page |
| **Add new page/tab** | `frontend/src/App.jsx`, create component in `pages/` |
| **Modify API calls** | `frontend/src/services/ragClient.js` |
| **Change UI theme** | `frontend/src/utils/themes.js`, `frontend/src/index.css` |
| **Add deployment check** | `preflight_check.sh` |
| **Modify schema handling** | `schema_manager.py` |

---

## File Count Summary

| Category | File Count |
|----------|-----------|
| Backend Python | ~50 files |
| Frontend React/TS | ~60 files |
| API Endpoints | 30+ endpoints in 2 files |
| Services | 8 service files |
| Core Modules | 4 core files |
| Components | 28+ React components |
| Documentation | 15+ documentation files |
| Scripts | 10+ utility/deployment scripts |
| Configuration | 15+ config files |

---

**Last Updated:** 2026-01-31
**Version:** 2-Tab UI (feature/2-tab-ui branch)

**Need more details about a specific file?** Check the inline docstrings in Python files or read CLAUDE.md for architectural overview.
