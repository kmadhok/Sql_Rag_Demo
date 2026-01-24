# Setup Prerequisites Guide

**SQL RAG System - Complete Setup Requirements**

This document provides a comprehensive reference of all prerequisites, dependencies, and setup requirements needed to run the SQL RAG system successfully.

---

## Table of Contents

1. [Quick Start Checklist](#quick-start-checklist)
2. [Required API Keys & Credentials](#required-api-keys--credentials)
3. [Required Data Files](#required-data-files)
4. [Generated Assets (Must Build Before First Run)](#generated-assets-must-build-before-first-run)
5. [Required Services & Infrastructure](#required-services--infrastructure)
6. [Environment Setup](#environment-setup)
7. [Configuration Files](#configuration-files)
8. [Dependency Matrix](#dependency-matrix)
9. [Step-by-Step Setup Guide](#step-by-step-setup-guide)
10. [Common Issues & Solutions](#common-issues--solutions)
11. [Minimal vs Full Setup](#minimal-vs-full-setup)

---

## Quick Start Checklist

Use this checklist to quickly verify all prerequisites are met:

- [ ] **Python 3.9+** installed (3.12 recommended)
- [ ] **Virtual environment** created and activated
- [ ] **Dependencies** installed via `pip install -r rag_app/requirements.txt`
- [ ] **GEMINI_API_KEY** set (Google Gemini API)
- [ ] **OPENAI_API_KEY** set (OpenAI embeddings)
- [ ] **Google Cloud credentials** configured (service account or gcloud)
- [ ] **Query CSV file** exists at `rag_app/sample_queries_with_metadata.csv`
- [ ] **Schema CSV file** exists at `rag_app/data_new/thelook_ecommerce_schema.csv`
- [ ] **FAISS vector store** generated using `standalone_embedding_generator.py`
- [ ] **BigQuery** enabled and configured (for SQL execution)
- [ ] **.env file** created with all required variables

---

## Required API Keys & Credentials

### 1. Google Gemini API (🔴 CRITICAL)

**Purpose:** Primary LLM for SQL generation, query rewriting, and chat responses

**Environment Variables:**
```bash
GEMINI_API_KEY=your-gemini-api-key
# OR for Vertex AI SDK mode:
GENAI_CLIENT_MODE=sdk
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

**Where to Get:**
- API Key Mode: https://makersuite.google.com/app/apikey
- Vertex AI Mode: Set up Google Cloud project with Vertex AI API enabled

**Configuration:**
- Set in `rag_app/.env` file
- OR export as environment variable: `export GEMINI_API_KEY=your-key`

**Used By:**
- `gemini_client.py` - LLM client for text generation
- `llm_registry.py` - Model selection and management
- `utils/embedding_provider.py` - Gemini embeddings (alternative to OpenAI)
- `simple_rag_simple_gemini.py` - RAG pipeline
- `chat_system.py` - Chat agent responses

**Failure Impact:**
- ❌ Application cannot start
- ❌ No SQL generation possible
- ❌ No chat responses

**Fallback:** None - this is mandatory

---

### 2. OpenAI API Key (🔴 CRITICAL for embeddings)

**Purpose:** Generate vector embeddings for semantic search

**Environment Variables:**
```bash
OPENAI_API_KEY=sk-your-openai-api-key
EMBEDDINGS_PROVIDER=openai  # Optional, defaults to openai
```

**Where to Get:**
- https://platform.openai.com/api-keys
- Requires billing enabled

**Configuration:**
- Set in `rag_app/.env` file
- OR export as environment variable: `export OPENAI_API_KEY=sk-your-key`

**Used By:**
- `openai_embedding_generator.py` - Embedding generation
- `utils/embedding_provider.py` - Embedding provider factory
- `standalone_embedding_generator.py` - Vector store creation
- `hybrid_retriever.py` - Hybrid search with embeddings

**Failure Impact:**
- ❌ Cannot generate vector embeddings
- ❌ Cannot build FAISS vector stores
- ❌ Application cannot perform semantic search

**Cost Estimate:**
- Model: `text-embedding-3-small`
- ~$0.02 per 1000 queries for initial embedding generation
- Cached after first generation

**Alternative:** Use Gemini embeddings (set `EMBEDDINGS_PROVIDER=gemini`)

---

### 3. Google Cloud Credentials (🟠 MAJOR for production features)

**Purpose:** Authentication for BigQuery, Firestore, and Vertex AI services

#### Option A: Service Account Key (Recommended for Cloud Run)

**Environment Variables:**
```bash
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account-key.json
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

**Setup Steps:**
1. Go to Google Cloud Console → IAM & Admin → Service Accounts
2. Create service account with required roles:
   - BigQuery Job User
   - BigQuery Data Viewer
   - Firestore User (if using conversation persistence)
   - Vertex AI User (if using Vertex AI SDK mode)
3. Create and download JSON key
4. Set `GOOGLE_APPLICATION_CREDENTIALS` to absolute path of key file

#### Option B: Application Default Credentials (for local development)

**Setup Command:**
```bash
gcloud auth application-default login
```

**Environment Variables:**
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
```

**Used By:**
- `core/bigquery_executor.py` - SQL execution against BigQuery
- `core/conversation_manager.py` - Firestore conversation storage
- `gemini_client.py` - Vertex AI SDK mode (optional)
- `utils/embedding_provider.py` - Gemini embeddings via Vertex AI

**Failure Impact:**
- ⚠️ BigQuery SQL execution unavailable (queries cannot be run)
- ⚠️ Firestore conversation persistence unavailable (falls back to in-memory)
- ⚠️ Vertex AI SDK mode unavailable (falls back to API key mode)

**Fallback:**
- BigQuery: Graceful failure with user-friendly error message
- Firestore: In-memory conversation storage (not persistent)

---

### 4. BigQuery Configuration (🟠 MAJOR for SQL execution)

**Purpose:** Execute generated SQL queries against BigQuery datasets

**Environment Variables:**
```bash
BIGQUERY_PROJECT_ID=your-billing-project-id
BIGQUERY_DATASET=bigquery-public-data.thelook_ecommerce
BIGQUERY_LOCATION=US  # Optional, default: US
```

**Required Setup:**
1. Enable BigQuery API in Google Cloud project
2. Ensure service account or user has permissions:
   - `bigquery.jobs.create` (run queries)
   - `bigquery.tables.getData` (read data)
3. Grant access to public dataset: `bigquery-public-data.thelook_ecommerce`

**Used By:**
- `core/bigquery_executor.py` - Query execution engine
- `services/sql_execution_service.py` - Service layer for SQL execution
- `app_simple_gemini.py` - UI SQL execution interface

**Failure Impact:**
- ⚠️ SQL execution fails
- ⚠️ Cannot display query results in UI
- ✅ SQL generation still works (generation separate from execution)

**Default Dataset:**
- `bigquery-public-data.thelook_ecommerce` (free public dataset)
- No billing for reading public datasets
- Billing only for query processing

**Cost Control:**
- Default max bytes billed: 100 MB
- Dry run mode available for cost estimation
- Query validation prevents expensive operations

---

## Required Data Files

### 1. Query CSV Source (🔴 CRITICAL)

**Path:** `rag_app/sample_queries_with_metadata.csv`

**Alternative Locations:**
- `rag_app/data_new/sample_queries_with_metadata.csv`
- `rag_app/data_new/sample_queries_with_metadata_recovered.csv`

**Required Columns:**
| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `query` | ✅ Yes | SQL query text | `SELECT * FROM users WHERE age > 21` |
| `description` | ⚠️ Recommended | Human-readable description | "Get adult users" |
| `tables` | ⚠️ Recommended | Comma-separated table names | "users" |
| `joins` | ❌ Optional | Join information (JSON or string) | `[{"left_table": "users", ...}]` |

**Configured In:**
- `config/app_config.py::CSV_PATH`
- Default: `Path(__file__).parent / "sample_queries_with_metadata.csv"`

**Used By:**
- `data/app_data_loader.py::load_csv_data()` - Primary data loading
- `standalone_embedding_generator.py` - Embedding generation source
- `catalog_analytics_generator.py` - Analytics pre-computation
- UI pages: Query Catalog, Data Explorer

**Failure Impact:**
- ❌ Application fails to start
- ❌ No queries available for search
- ❌ Empty Query Catalog

**Format Example:**
```csv
query,description,tables,joins
"SELECT user_id, COUNT(*) FROM orders GROUP BY user_id","Count orders per user","orders",""
"SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id","User orders with totals","users,orders","[{""left_table"":""users"",""right_table"":""orders""}]"
```

---

### 2. Schema CSV (🟡 WARNING if missing)

**Path:** `rag_app/data_new/thelook_ecommerce_schema.csv`

**Alternative:** `rag_app/schema.csv`

**Required Columns:**
| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `table_id` or `full_table_name` | ✅ Yes | Table identifier | `users` or `project.dataset.users` |
| `column` | ✅ Yes | Column name | `user_id` |
| `datatype` | ✅ Yes | Column data type | `INT64`, `STRING`, `TIMESTAMP` |

**Configured In:**
- `config/app_config.py::SCHEMA_CSV_PATH`
- Default: `Path(__file__).parent / "data_new/thelook_ecommerce_schema.csv"`

**Used By:**
- `schema_manager.py::SchemaManager` - Schema-aware retrieval
- `core/sql_validator.py` - Table/column validation
- `core/bigquery_executor.py` - Table name validation
- `standalone_embedding_generator.py` - Schema-enhanced embeddings

**Failure Impact:**
- ⚠️ SQL validation shows warnings (non-blocking)
- ⚠️ Schema injection unavailable (reduced search quality)
- ⚠️ Falls back to hardcoded table list
- ✅ Application continues to function

**Fallback Behavior:**
- Uses hardcoded table list from `VALID_TABLES` constant
- Basic validation still works
- Schema browser UI unavailable

**Format Example:**
```csv
table_id,column,datatype
users,user_id,INT64
users,email,STRING
users,created_at,TIMESTAMP
orders,order_id,INT64
orders,user_id,INT64
orders,total_amount,FLOAT64
```

**How to Generate:**
You can extract schema from BigQuery:
```sql
SELECT
  table_name as table_id,
  column_name as column,
  data_type as datatype
FROM `project.dataset.INFORMATION_SCHEMA.COLUMNS`
ORDER BY table_name, ordinal_position
```

---

### 3. LookML Safe Join Map (❌ Optional)

**Path:** `rag_app/faiss_indices/lookml_safe_join_map.json`

**Alternative:** `rag_app/lookml_safe_join_map.json`

**Purpose:** Enhanced SQL generation with LookML-style join patterns

**Structure:**
```json
{
  "project": "thelook_ecommerce",
  "explores": {
    "users": {
      "base_table": "users",
      "label": "Users",
      "joins": {
        "orders": {
          "sql_on": "${users.id} = ${orders.user_id}",
          "relationship": "one_to_many",
          "join_type": "LEFT OUTER"
        }
      }
    }
  },
  "join_graph": {
    "users": ["orders", "events"],
    "orders": ["order_items", "users"]
  }
}
```

**Used By:**
- `data/app_data_loader.py::load_lookml_safe_join_map()` - Load join mappings
- `app_simple_gemini.py::handle_schema_query()` - @schema agent queries
- RAG prompts - Enhanced SQL generation with join hints

**Failure Impact:**
- ⚠️ @schema agent unavailable
- ⚠️ Join hints not included in SQL generation prompts
- ✅ Core functionality unaffected

**Generated By:**
- LookML parsing scripts (if using LookML source)
- Manual creation based on database schema

---

## Generated Assets (Must Build Before First Run)

### 1. FAISS Vector Indices (🔴 CRITICAL - MUST GENERATE)

**Purpose:** Enable semantic search over SQL queries using vector embeddings

**Directory:** `rag_app/faiss_indices/`

**Generated Structure:**
```
faiss_indices/
├── index_sample_queries_with_metadata/
│   ├── index.faiss          # FAISS vector index (binary)
│   ├── index.pkl            # Metadata and document store
│   └── embedding_stats.json # Embedding generation statistics
└── status_sample_queries_with_metadata.json  # Processing status
```

**Generation Command:**
```bash
cd rag_app
python standalone_embedding_generator.py --csv "sample_queries_with_metadata.csv"
```

**Generation Requirements:**
- ✅ `OPENAI_API_KEY` environment variable set
- ✅ Source CSV file exists
- ✅ 100-500 MB available disk space
- ⏱️ Estimated time: 5-30 minutes (depending on query count)
- 💰 Cost: ~$0.02 per 1000 queries (one-time)

**Advanced Options:**
```bash
# Incremental update (only process new queries)
python standalone_embedding_generator.py \
  --csv "sample_queries_with_metadata.csv" \
  --incremental

# Force complete rebuild
python standalone_embedding_generator.py \
  --csv "sample_queries_with_metadata.csv" \
  --force-rebuild

# Use Gemini embeddings instead of OpenAI
export EMBEDDINGS_PROVIDER=gemini
python standalone_embedding_generator.py \
  --csv "sample_queries_with_metadata.csv"
```

**Used By:**
- `data/app_data_loader.py::load_vector_store()` - Load into memory
- `hybrid_retriever.py` - Hybrid vector + keyword search
- `simple_rag_simple_gemini.py` - RAG retrieval pipeline
- All search and chat functionality

**Failure Impact:**
- ❌ Application fails to start with error: "Vector store not found"
- ❌ No semantic search possible
- ❌ Chat and Query Search pages unusable

**Verification:**
Check if vector store exists:
```bash
ls -lh rag_app/faiss_indices/index_sample_queries_with_metadata/
# Should show: index.faiss, index.pkl
```

**Re-generation Triggers:**
- Source CSV modified (new queries added)
- Embedding model changed
- Corrupted index files

---

### 2. Catalog Analytics Cache (🟢 OPTIONAL - Improves Performance)

**Purpose:** Pre-compute analytics for Query Catalog page to reduce load time

**Directory:** `rag_app/catalog_analytics/`

**Generated Files:**
```
catalog_analytics/
├── join_analysis.json           # Join statistics and patterns
├── table_usage_stats.json       # Table frequency analysis
├── optimized_queries.parquet    # Parsed query metadata (fast loading)
├── relationships_graph.svg      # Visual join relationship graph
├── relationships_graph.png      # PNG version of graph
└── cache_metadata.json          # Cache generation metadata
```

**Generation Command:**
```bash
cd rag_app
python catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv"
```

**Generation Requirements:**
- ✅ Source CSV exists
- ✅ Optional: `graphviz` library for graph generation
- ⏱️ Estimated time: 1-5 minutes

**Used By:**
- `data/app_data_loader.py::load_cached_analytics()` - Load pre-computed analytics
- `ui/pages.py::create_query_catalog_page()` - Display catalog statistics
- `app_simple_gemini.py::display_join_analysis()` - Show join analysis

**Failure Impact:**
- ⚠️ Query Catalog page loads slower (~5-10 seconds delay)
- ⚠️ Join graphs not available
- ✅ Generates analytics on-the-fly (fallback)

**Benefits:**
- ⚡ 10x faster Query Catalog page load
- 📊 Pre-rendered join relationship graphs
- 💾 Reduced memory usage during runtime

**Re-generation Triggers:**
- Source CSV updated
- Want to refresh statistics
- Adding new analytics features

---

### 3. LLM Response Cache (✅ AUTO-GENERATED)

**Purpose:** Cache Gemini API responses to reduce costs and latency

**Directory:** `rag_app/llm_sql_cache/`

**Structure:**
```
llm_sql_cache/
├── cache_<hash1>.json
├── cache_<hash2>.json
└── ...
```

**Generation:** Automatic on first query
- No manual action needed
- Created during first application run
- Grows over time as queries are processed

**Cache Key:** Hash of (prompt + model + temperature)

**Used By:**
- `gemini_client.py::GeminiClient` - Response caching layer
- All LLM generation calls

**Failure Impact:** None - directory created automatically

**Benefits:**
- 💰 Reduced API costs (free cache hits)
- ⚡ Faster response times for repeated queries
- 🔒 Works offline for cached queries

**Clearing Cache:**
```bash
# Clear all cached responses
rm -rf rag_app/llm_sql_cache/

# Clear specific cached responses (by date)
find rag_app/llm_sql_cache/ -mtime +30 -delete  # Older than 30 days
```

---

## Required Services & Infrastructure

### 1. Google Cloud Platform Services

#### A. BigQuery (🟠 MAJOR - for SQL execution)

**Purpose:** Execute generated SQL queries against real datasets

**Setup Steps:**

1. **Enable BigQuery API**
   ```bash
   gcloud services enable bigquery.googleapis.com
   ```

2. **Create/Configure Service Account**
   ```bash
   # Create service account
   gcloud iam service-accounts create sql-rag-bigquery \
     --display-name="SQL RAG BigQuery Access"

   # Grant BigQuery Job User role (to run queries)
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:sql-rag-bigquery@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/bigquery.jobUser"

   # Download key
   gcloud iam service-accounts keys create ~/sql-rag-key.json \
     --iam-account=sql-rag-bigquery@PROJECT_ID.iam.gserviceaccount.com
   ```

3. **Set Environment Variable**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="$HOME/sql-rag-key.json"
   ```

**Required Permissions:**
- `bigquery.jobs.create` - Create and run query jobs
- `bigquery.tables.getData` - Read table data
- `bigquery.tables.get` - Get table metadata

**Default Dataset:**
- `bigquery-public-data.thelook_ecommerce` (free public dataset)
- No billing for reading public data
- Billing only for query processing bytes

**Cost Control:**
- Default max bytes billed: 100 MB per query
- Dry run mode available (estimates cost without running)
- Query validator prevents expensive operations

**Used By:**
- `core/bigquery_executor.py::BigQueryExecutor`
- `services/sql_execution_service.py`
- Query Search and Chat UI execution interfaces

**Failure Impact:**
- ⚠️ SQL execution unavailable
- ⚠️ "Execute Query" button shows error
- ✅ SQL generation still works

---

#### B. Firestore (🟢 OPTIONAL - for conversation persistence)

**Purpose:** Persist chat conversations across sessions

**Setup Steps:**

1. **Enable Firestore API**
   ```bash
   gcloud services enable firestore.googleapis.com
   ```

2. **Create Firestore Database**
   - Go to Cloud Console → Firestore
   - Select "Native Mode" (not Datastore mode)
   - Choose region (e.g., `us-central1`)

3. **Grant Service Account Permissions**
   ```bash
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:sql-rag-bigquery@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/datastore.user"
   ```

**Used By:**
- `core/conversation_manager.py::ConversationManager`
- Chat page conversation save/load functionality

**Failure Impact:**
- ⚠️ Conversations not persisted (in-memory only)
- ⚠️ Save/load conversation buttons unavailable
- ✅ Chat functionality works with in-memory storage

**Fallback:**
- Automatically falls back to in-memory storage
- User-friendly warning displayed in UI

**Cost:**
- Free tier: 50K reads + 20K writes per day
- Typical usage: ~10-100 operations per user session

---

#### C. Vertex AI (❌ OPTIONAL - alternative to API key)

**Purpose:** Use Vertex AI SDK instead of direct Gemini API

**Setup Steps:**

1. **Enable Vertex AI API**
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

2. **Set Environment Variables**
   ```bash
   export GENAI_CLIENT_MODE=sdk
   export GOOGLE_CLOUD_PROJECT=your-project-id
   export GOOGLE_CLOUD_LOCATION=us-central1
   ```

**Advantages:**
- Better quota management
- Enterprise support
- Integrated with other GCP services

**Used By:**
- `gemini_client.py` (when `GENAI_CLIENT_MODE=sdk`)

**Fallback:**
- Use API key mode: `GENAI_CLIENT_MODE=api`

---

### 2. External APIs

#### OpenAI API

**Purpose:** Generate embeddings for vector search

**Requirements:**
- Active OpenAI account
- Billing enabled
- API key with sufficient quota

**Rate Limits:**
- Free tier: 3 requests/minute
- Paid tier: 3,000 requests/minute

**Cost (text-embedding-3-small):**
- $0.00002 per 1,000 tokens
- ~$0.02 per 1,000 queries (one-time embedding generation)

**Alternative:** Gemini embeddings (set `EMBEDDINGS_PROVIDER=gemini`)

---

## Environment Setup

### 1. Python Version

**Required:** Python 3.9 or higher
**Recommended:** Python 3.12 (as specified in `.python-version`)

**Installation with pyenv:**
```bash
# Install pyenv (if not already installed)
curl https://pyenv.run | bash

# Install Python 3.12
pyenv install 3.12.0

# Set local Python version for project
cd /path/to/SQL_RAG
pyenv local 3.12.0

# Verify
python --version  # Should show: Python 3.12.0
```

**Alternative Installation:**
- System Python: `sudo apt install python3.12` (Ubuntu/Debian)
- Homebrew: `brew install python@3.12` (macOS)
- Official installer: https://www.python.org/downloads/

---

### 2. Virtual Environment (Recommended)

**Create Virtual Environment:**
```bash
cd rag_app
python -m venv venv
```

**Activate:**
```bash
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**Verify:**
```bash
which python  # Should point to venv/bin/python
```

**Deactivate:**
```bash
deactivate
```

---

### 3. Python Dependencies

**Production Dependencies** (`rag_app/requirements.txt`):

#### Core Framework
- `streamlit>=1.28.0` - Web application framework
- `pandas>=2.0.0` - Data processing
- `numpy>=1.24.0` - Numerical operations

#### AI/ML Stack
- `google-genai>=1.0.0` - **NEW** Gemini SDK (primary client)
- `google-generativeai>=0.8.0` - Legacy Gemini client
- `langchain>=0.1.0` - LangChain framework
- `langchain-openai>=0.1.0` - OpenAI integrations
- `langchain-community>=0.0.20` - Community integrations
- `openai>=1.0.0` - OpenAI API client

#### Vector Store
- `faiss-cpu>=1.7.0` - FAISS vector search (CPU-optimized for Cloud Run)
- `rank-bm25>=0.2.0` - BM25 keyword search for hybrid retrieval

#### Google Cloud
- `google-cloud-firestore>=2.13.0` - Firestore database
- `google-cloud-bigquery>=3.0.0` - BigQuery client
- `google-cloud-bigquery[pandas]>=3.0.0` - BigQuery with Pandas support

#### Text Processing
- `sqlparse>=0.4.0` - SQL parsing and formatting
- `rapidfuzz>=3.0.0` - Fast fuzzy string matching
- `pyarrow>=10.0.0` - Parquet file support

#### Utilities
- `python-dotenv>=1.0.0` - Environment variable loading
- `requests>=2.28.0` - HTTP client

**Installation:**
```bash
cd rag_app
pip install -r requirements.txt
```

**Test Dependencies** (`requirements-test.txt`):
```bash
pip install -r requirements-test.txt
```

Includes:
- `pytest>=7.4.0` - Testing framework
- `pytest-mock>=3.12.0` - Mocking support
- `pytest-cov>=4.1.0` - Coverage reporting

---

### 4. Environment Variables

**Create `.env` file** in `rag_app/` directory:

```bash
# ========================================
# GOOGLE GEMINI / GENAI CLIENT
# ========================================
# Mode: "sdk" (Vertex AI) or "api" (direct API key)
GENAI_CLIENT_MODE=sdk

# API Key (required if GENAI_CLIENT_MODE=api)
GEMINI_API_KEY=AIza...your-gemini-api-key

# Alternative API key variable name
GOOGLE_API_KEY=AIza...your-gemini-api-key

# ========================================
# GOOGLE CLOUD PROJECT
# ========================================
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account-key.json

# ========================================
# EMBEDDINGS CONFIGURATION
# ========================================
EMBEDDINGS_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...your-openai-api-key

# Alternative: Use Gemini embeddings
# EMBEDDINGS_PROVIDER=gemini

# ========================================
# BIGQUERY CONFIGURATION
# ========================================
BIGQUERY_PROJECT_ID=your-project-id
BIGQUERY_DATASET=bigquery-public-data.thelook_ecommerce
BIGQUERY_LOCATION=US

# ========================================
# LLM MODEL SELECTION (OPTIONAL)
# ========================================
# Models for different pipeline stages
LLM_GEN_MODEL=gemini-2.5-pro              # SQL generation
LLM_PARSE_MODEL=gemini-2.5-flash-lite     # Query parsing
LLM_REWRITE_MODEL=gemini-2.5-flash-lite   # Query rewriting
LLM_CHAT_MODEL=gemini-2.5-flash-lite      # Chat responses

# ========================================
# PERFORMANCE TUNING (OPTIONAL)
# ========================================
EMBEDDING_TIMEOUT_SECONDS=15
CHAT_SCHEMA_DOC_LIMIT=25
UI_ADVANCED_DEFAULT=0  # 0=simple, 1=advanced mode default

# ========================================
# DEVELOPMENT/DEBUG (OPTIONAL)
# ========================================
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

**Template Location:** `rag_app/.env.example` (if available)

**Security:**
- ⚠️ **Never commit `.env` to git**
- Add to `.gitignore`: `*.env`
- Use different `.env` files for dev/staging/production

---

## Configuration Files

### 1. .env File (🔴 REQUIRED)

**Location:** `rag_app/.env`

**Purpose:** Store sensitive credentials and configuration

**Must Configure:**
- API keys (Gemini, OpenAI)
- Google Cloud project settings
- BigQuery configuration

**Security Best Practices:**
- Never commit to version control
- Use different keys for dev/prod
- Rotate keys periodically
- Restrict file permissions: `chmod 600 .env`

---

### 2. Streamlit Configuration (✅ AUTO-CONFIGURED)

**Location:** `rag_app/.streamlit/config.toml`

**Purpose:** UI theme and server settings

**Default Configuration:**
```toml
[theme]
primaryColor = "#8B5CF6"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F3F4F6"
textColor = "#1F2937"
font = "sans serif"

[server]
port = 8501
enableCORS = false
enableXsrfProtection = true
```

**Customization:**
- Modify colors to match branding
- Change default port
- Enable/disable CORS for API integration

---

### 3. pytest Configuration (for testing)

**Location:** `pytest.ini` (root directory)

**Markers:**
- `integration` - Real API integration tests
- `e2e` - Unit tests with mocked components
- `chat`, `sql`, `catalog`, `agent` - Feature categories
- `slow` - Long-running tests

**Usage:**
```bash
pytest -m integration  # Run integration tests only
pytest -m "not slow"   # Skip slow tests
```

---

## Dependency Matrix

**Impact Analysis: What Breaks if Missing?**

| Component | Severity | Impact | Fallback Available |
|-----------|----------|--------|-------------------|
| **GEMINI_API_KEY** | 🔴 CRITICAL | App won't start, no LLM generation | ❌ None |
| **OPENAI_API_KEY** | 🔴 CRITICAL | Can't generate embeddings, no vector store | ⚠️ Use Gemini embeddings |
| **Vector Store (FAISS)** | 🔴 CRITICAL | App won't start, no retrieval | ❌ Must generate |
| **Query CSV** | 🔴 CRITICAL | App won't start, no data | ❌ Must provide |
| **Schema CSV** | 🟡 WARNING | Validation warnings, reduced quality | ✅ Hardcoded table list |
| **Google Cloud Credentials** | 🟠 MAJOR | No BigQuery/Firestore | ✅ Graceful degradation |
| **BigQuery Setup** | 🟠 MAJOR | SQL execution fails | ✅ Shows error message |
| **Firestore** | 🟢 MINOR | No conversation persistence | ✅ In-memory storage |
| **Analytics Cache** | 🟢 MINOR | Slower UI load times | ✅ Generates on-the-fly |
| **LookML Join Map** | 🟢 MINOR | No @schema agent | ✅ Basic SQL generation |

---

## Step-by-Step Setup Guide

### First-Time Complete Setup

#### Step 1: Install Python 3.12
```bash
# Using pyenv (recommended)
pyenv install 3.12.0
pyenv local 3.12.0

# Verify
python --version  # Should show: Python 3.12.0
```

#### Step 2: Create Virtual Environment
```bash
cd rag_app
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

#### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(streamlit|langchain|faiss|google-genai)"
```

#### Step 4: Obtain API Keys

**A. Google Gemini API Key**
1. Go to https://makersuite.google.com/app/apikey
2. Create new API key
3. Copy key (starts with `AIza...`)

**B. OpenAI API Key**
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy key (starts with `sk-proj...`)

#### Step 5: Set Up Google Cloud (for production features)

**A. Create/Select Project**
```bash
# Create new project
gcloud projects create sql-rag-project --name="SQL RAG System"

# Set as active project
gcloud config set project sql-rag-project
```

**B. Enable Required APIs**
```bash
gcloud services enable bigquery.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

**C. Create Service Account**
```bash
# Create service account
gcloud iam service-accounts create sql-rag-sa \
  --display-name="SQL RAG Service Account"

# Grant roles
gcloud projects add-iam-policy-binding sql-rag-project \
  --member="serviceAccount:sql-rag-sa@sql-rag-project.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

gcloud projects add-iam-policy-binding sql-rag-project \
  --member="serviceAccount:sql-rag-sa@sql-rag-project.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

# Download key
gcloud iam service-accounts keys create ~/sql-rag-key.json \
  --iam-account=sql-rag-sa@sql-rag-project.iam.gserviceaccount.com
```

#### Step 6: Configure Environment Variables
```bash
# Copy template
cp .env.example .env

# Edit .env file with your credentials
nano .env  # or use your preferred editor
```

**Minimal .env Configuration:**
```bash
GEMINI_API_KEY=AIza...your-key
OPENAI_API_KEY=sk-proj...your-key
GOOGLE_APPLICATION_CREDENTIALS=/home/user/sql-rag-key.json
GOOGLE_CLOUD_PROJECT=sql-rag-project
BIGQUERY_PROJECT_ID=sql-rag-project
```

#### Step 7: Verify Data Files Exist
```bash
# Check query CSV
ls -lh sample_queries_with_metadata.csv

# Check schema CSV
ls -lh data_new/thelook_ecommerce_schema.csv

# If missing, check alternative locations or request sample data
```

#### Step 8: Generate FAISS Vector Store (CRITICAL)
```bash
# This is MANDATORY before first run
python standalone_embedding_generator.py \
  --csv "sample_queries_with_metadata.csv"

# Expected output:
# ✅ Loaded 1234 queries
# ✅ Generated embeddings (1234/1234)
# ✅ Vector store saved to faiss_indices/index_sample_queries_with_metadata/
```

**⏱️ This takes 5-30 minutes depending on query count**

#### Step 9: (Optional) Generate Analytics Cache
```bash
python catalog_analytics_generator.py \
  --csv "sample_queries_with_metadata.csv"

# Expected output:
# ✅ Generated join analysis
# ✅ Generated optimized queries
# ✅ Generated relationship graphs
```

#### Step 10: Verify Setup
```bash
# Check all prerequisites
python -c "
import streamlit
import langchain
import faiss
import google.generativeai as genai
print('✅ All core dependencies installed')
"

# Check environment variables
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
assert os.getenv('GEMINI_API_KEY'), '❌ GEMINI_API_KEY not set'
assert os.getenv('OPENAI_API_KEY'), '❌ OPENAI_API_KEY not set'
print('✅ Environment variables configured')
"

# Check vector store
ls faiss_indices/index_sample_queries_with_metadata/index.faiss || echo "❌ Vector store not generated"
```

#### Step 11: Run Application
```bash
streamlit run app_simple_gemini.py
```

**Expected Output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.x:8501
```

#### Step 12: Test Application
1. Open http://localhost:8501 in browser
2. Navigate to "Query Search" page
3. Enter test query: "Write SQL to join users and orders"
4. Click "Generate SQL"
5. Verify SQL is generated
6. Click "Execute Query" to test BigQuery integration

---

### Quick Development Setup (Minimal)

For local development without BigQuery/Firestore:

```bash
# 1. Install Python + create venv
python3.12 -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r rag_app/requirements.txt

# 3. Set minimal environment variables
cat > rag_app/.env << EOF
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
EOF

# 4. Generate vector store (REQUIRED)
cd rag_app
python standalone_embedding_generator.py --csv "sample_queries_with_metadata.csv"

# 5. Run app
streamlit run app_simple_gemini.py
```

**What Works:**
- ✅ Query Search (SQL generation)
- ✅ Chat interface
- ✅ Query Catalog browsing

**What Doesn't Work:**
- ❌ SQL execution (no BigQuery)
- ❌ Conversation persistence (no Firestore)

---

## Common Issues & Solutions

### Issue 1: "Vector store not found"

**Error Message:**
```
FileNotFoundError: Vector store not found at faiss_indices/index_sample_queries_with_metadata
```

**Cause:** FAISS indices not generated

**Solution:**
```bash
cd rag_app
python standalone_embedding_generator.py --csv "sample_queries_with_metadata.csv"
```

**Verification:**
```bash
ls faiss_indices/index_sample_queries_with_metadata/
# Should show: index.faiss, index.pkl
```

---

### Issue 2: "OPENAI_API_KEY not set"

**Error Message:**
```
ValueError: OPENAI_API_KEY environment variable not set
```

**Cause:** Missing or incorrectly named environment variable

**Solution:**
```bash
# Check if variable is set
echo $OPENAI_API_KEY

# If empty, export it
export OPENAI_API_KEY=sk-proj-your-key

# Or add to .env file
echo "OPENAI_API_KEY=sk-proj-your-key" >> rag_app/.env
```

**Verification:**
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"
```

---

### Issue 3: "GEMINI_API_KEY not set"

**Error Message:**
```
ValueError: GEMINI_API_KEY not set and GENAI_CLIENT_MODE is 'api'
```

**Cause:** Missing Gemini credentials

**Solution:**
```bash
# Get API key from https://makersuite.google.com/app/apikey

# Export as environment variable
export GEMINI_API_KEY=AIza-your-key

# Or add to .env file
echo "GEMINI_API_KEY=AIza-your-key" >> rag_app/.env
```

**Alternative (Vertex AI SDK mode):**
```bash
export GENAI_CLIENT_MODE=sdk
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

---

### Issue 4: "BigQuery permission denied"

**Error Message:**
```
google.api_core.exceptions.PermissionDenied: 403 User does not have permission to query table
```

**Cause:** Missing Google Cloud credentials or insufficient permissions

**Solutions:**

**A. Check credentials are set:**
```bash
echo $GOOGLE_APPLICATION_CREDENTIALS
# Should show path to service account key JSON
```

**B. Authenticate with gcloud:**
```bash
gcloud auth application-default login
```

**C. Verify service account has correct roles:**
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:YOUR_SA_EMAIL"
```

**D. Grant required permissions:**
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SA_EMAIL" \
  --role="roles/bigquery.jobUser"
```

---

### Issue 5: "Schema file not found"

**Error Message:**
```
WARNING: Schema CSV not found at data_new/thelook_ecommerce_schema.csv
```

**Cause:** Schema CSV file missing or at different location

**Impact:** Non-critical - falls back to hardcoded tables

**Solution:**

**A. Check if file exists at alternative location:**
```bash
find rag_app/ -name "*schema*.csv"
```

**B. Update config to point to correct path:**
Edit `rag_app/config/app_config.py`:
```python
SCHEMA_CSV_PATH = Path(__file__).parent / "your/actual/schema.csv"
```

**C. Generate schema from BigQuery:**
```sql
SELECT
  table_name as table_id,
  column_name as column,
  data_type as datatype
FROM `your-project.your-dataset.INFORMATION_SCHEMA.COLUMNS`
```
Save results as CSV.

---

### Issue 6: "Module not found" errors

**Error Message:**
```
ModuleNotFoundError: No module named 'streamlit'
```

**Cause:** Dependencies not installed or wrong Python environment

**Solution:**
```bash
# Verify you're in virtual environment
which python  # Should show venv/bin/python

# If not, activate venv
source venv/bin/activate

# Install dependencies
pip install -r rag_app/requirements.txt

# Verify installation
pip list | grep streamlit
```

---

### Issue 7: "Firestore unavailable" warning

**Warning Message:**
```
WARNING: Firestore unavailable - using in-memory storage
```

**Cause:** Firestore not configured or credentials missing

**Impact:** Conversations not persisted across sessions

**Solution (if you need persistence):**

**A. Enable Firestore API:**
```bash
gcloud services enable firestore.googleapis.com
```

**B. Create Firestore database:**
- Go to Cloud Console → Firestore
- Create database in Native mode

**C. Grant service account permissions:**
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:YOUR_SA_EMAIL" \
  --role="roles/datastore.user"
```

**Alternative:** Ignore warning if you don't need persistence

---

### Issue 8: Port 8501 already in use

**Error Message:**
```
OSError: [Errno 48] Address already in use
```

**Cause:** Another Streamlit instance or application using port 8501

**Solution:**

**A. Find and kill existing process:**
```bash
# Find process using port 8501
lsof -i :8501

# Kill process
kill -9 <PID>
```

**B. Use different port:**
```bash
streamlit run app_simple_gemini.py --server.port 8502
```

---

### Issue 9: Slow embedding generation

**Symptom:** Vector store generation takes hours

**Cause:** Rate limiting or large query count

**Solutions:**

**A. Check rate limits:**
- OpenAI free tier: 3 requests/minute
- Consider upgrading to paid tier

**B. Use incremental mode:**
```bash
python standalone_embedding_generator.py \
  --csv "queries.csv" \
  --incremental
```

**C. Switch to Gemini embeddings:**
```bash
export EMBEDDINGS_PROVIDER=gemini
python standalone_embedding_generator.py --csv "queries.csv"
```

---

### Issue 10: Out of memory during FAISS index creation

**Error Message:**
```
MemoryError: Unable to allocate array
```

**Cause:** Large vector store exceeds available RAM

**Solutions:**

**A. Increase system memory**

**B. Use batch processing:**
Split CSV into smaller chunks and generate multiple indices

**C. Use FAISS IVF index (approximate):**
Modify `standalone_embedding_generator.py` to use IVF index type

---

## Minimal vs Full Setup

### Minimal Setup (Local Development)

**Use Case:** Quick testing, development, demos

**Requirements:**
- ✅ Python 3.9+
- ✅ `GEMINI_API_KEY`
- ✅ `OPENAI_API_KEY`
- ✅ Query CSV file
- ✅ Generated FAISS vector store

**Optional:**
- ⚠️ Schema CSV (falls back to hardcoded tables)
- ❌ Google Cloud credentials
- ❌ BigQuery setup
- ❌ Firestore
- ❌ Analytics cache

**What Works:**
- ✅ Query Search (SQL generation)
- ✅ Chat interface with agents
- ✅ Query Catalog browsing
- ✅ Vector search and retrieval

**What Doesn't Work:**
- ❌ SQL execution against BigQuery
- ❌ Conversation persistence
- ❌ Schema browser (reduced functionality)

**Setup Time:** ~15-30 minutes (including vector generation)

**Estimated Cost:** $0.02-0.10 one-time (embedding generation)

---

### Full Production Setup

**Use Case:** Production deployment, full features, team usage

**Requirements:**
- ✅ All minimal requirements
- ✅ Google Cloud service account with key
- ✅ BigQuery API enabled and configured
- ✅ Firestore database created
- ✅ Schema CSV file
- ✅ Analytics cache pre-generated
- ✅ LookML join map (if using LookML)

**What Works:**
- ✅ Everything in minimal setup
- ✅ SQL execution with results
- ✅ Conversation persistence
- ✅ Full schema browser
- ✅ Advanced validation
- ✅ @schema agent
- ✅ Production monitoring

**Setup Time:** ~1-2 hours (including GCP setup)

**Ongoing Costs:**
- BigQuery: ~$0.00-0.10 per query (public dataset is free)
- Firestore: Free tier covers most usage
- Gemini API: $0.000075-0.0003 per 1K tokens
- OpenAI embeddings: One-time $0.02 per 1K queries

---

## Next Steps After Setup

### 1. Verify Everything Works

**Run Health Check:**
```bash
cd rag_app
python -c "
from data.app_data_loader import load_vector_store, load_csv_data, load_schema_manager

# Test vector store
vs = load_vector_store('index_sample_queries_with_metadata')
print(f'✅ Vector store loaded: {vs.index.ntotal} documents')

# Test CSV data
csv = load_csv_data()
print(f'✅ CSV data loaded: {len(csv)} queries')

# Test schema manager
sm = load_schema_manager()
print(f'✅ Schema manager loaded: {sm.table_count if sm else 0} tables')
"
```

### 2. Test End-to-End Flow

**A. Test Query Search:**
1. Start app: `streamlit run app_simple_gemini.py`
2. Go to "Query Search" page
3. Enter: "Write SQL to find top 10 products by sales"
4. Verify SQL is generated

**B. Test Chat:**
1. Go to "Chat" page
2. Send message: "@explain What is a LEFT JOIN?"
3. Verify agent responds with explanation

**C. Test SQL Execution:**
1. Generate SQL query
2. Click "Execute Query"
3. Verify results are displayed

### 3. Customize Configuration

**Update Models:**
```bash
# Use faster models for development
export LLM_GEN_MODEL=gemini-2.5-flash-lite
export LLM_CHAT_MODEL=gemini-2.5-flash-lite
```

**Adjust UI Settings:**
Edit `rag_app/.streamlit/config.toml` to customize theme

### 4. Add Your Own Data

**Prepare Your CSV:**
```csv
query,description,tables,joins
"SELECT * FROM my_table","Get all records","my_table",""
```

**Generate Embeddings:**
```bash
python standalone_embedding_generator.py --csv "my_data.csv"
```

**Update Config:**
```python
# In config/app_config.py
DEFAULT_VECTOR_STORE = "index_my_data"
CSV_PATH = Path(__file__).parent / "my_data.csv"
```

### 5. Monitor Usage

**Check Token Usage:**
- View session stats in UI footer
- Monitor LLM cache directory growth
- Review BigQuery job history

**Check Costs:**
```bash
# BigQuery costs
gcloud billing accounts describe ACCOUNT_ID --format="table(displayName,state)"

# Review query costs in Cloud Console
```

### 6. Set Up Testing

**Install Test Dependencies:**
```bash
pip install -r requirements-test.txt
```

**Run Tests:**
```bash
# Unit tests (fast)
pytest tests/e2e/ -v

# Integration tests (slow, requires API keys)
pytest tests/integration/ -v -m integration
```

---

## Additional Resources

### Documentation
- Main README: `SQL_RAG/README.md` (if available)
- CLAUDE.md: Project guidance for AI assistants
- Deployment Guide: `rag_app/DEPLOYMENT_GUIDE.md`

### Google Cloud
- BigQuery Quickstart: https://cloud.google.com/bigquery/docs/quickstarts
- Firestore Documentation: https://cloud.google.com/firestore/docs
- Service Accounts: https://cloud.google.com/iam/docs/service-accounts

### API Documentation
- Google Gemini API: https://ai.google.dev/docs
- OpenAI API: https://platform.openai.com/docs
- LangChain: https://python.langchain.com/docs

### Tools
- Streamlit Documentation: https://docs.streamlit.io
- FAISS Documentation: https://github.com/facebookresearch/faiss/wiki

---

## Support & Troubleshooting

### Getting Help

1. **Check this document** for common issues
2. **Review logs** in terminal output
3. **Enable debug logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```
4. **Check environment variables:**
   ```bash
   python -c "import os; print({k:v for k,v in os.environ.items() if 'API' in k or 'GOOGLE' in k})"
   ```

### Debug Mode

Enable verbose logging:
```bash
export LOG_LEVEL=DEBUG
streamlit run app_simple_gemini.py
```

### Contact

- File issues on GitHub repository
- Review existing issues for solutions
- Consult CLAUDE.md for architecture details

---

**Last Updated:** 2025-01-03
**Document Version:** 1.0
**Maintained By:** SQL RAG Team
