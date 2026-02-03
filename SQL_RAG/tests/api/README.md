# API Endpoint Tests

**Comprehensive test suite for SQL RAG FastAPI endpoints with REAL services.**

## Overview

This directory contains **API endpoint tests** that validate the **HTTP layer** of the FastAPI backend with **real services** (no mocks). These tests use `TestClient` to make HTTP requests and verify:

- ✅ Request/response format and validation
- ✅ HTTP status codes (200, 201, 404, 422, 503)
- ✅ Pydantic model serialization
- ✅ Integration with real backend services (FAISS, Gemini, BigQuery, Firestore)
- ✅ Error handling and edge cases

## 🎯 What These Tests Validate

| Test Category | What's Tested | Real Services Used |
|--------------|---------------|-------------------|
| **Health Checks** | Service availability, dashboard integrity | Firestore |
| **Query Endpoints** | RAG query search, quick answers | FAISS, Gemini, SchemaManager |
| **SQL Execution** | BigQuery SQL execution, validation | BigQuery, SchemaManager |
| **SQL Assistant** | AI-powered explain/fix/complete/format/chat | Gemini, SchemaManager |
| **Schema Exploration** | List tables, columns, AI descriptions | SchemaManager, Gemini |
| **Saved Queries** | CRUD operations for saved queries | Firestore |
| **Dashboards** | CRUD operations for dashboards | Firestore |

---

## 📁 Test Files

```
tests/api/
├── conftest.py                          # Shared fixtures (TestClient, cleanup helpers)
├── test_health_endpoints.py             # GET /health, GET /health/dashboard
├── test_query_endpoints.py              # POST /query/search, POST /query/quick
├── test_sql_execution_endpoints.py      # POST /sql/execute
├── test_sql_assistant_endpoints.py      # POST /sql/explain, fix, complete, format, chat
├── test_schema_endpoints.py             # GET /schema/tables, columns, description
├── test_saved_query_endpoints.py        # POST/GET/GET{id} /saved_queries
├── test_dashboard_endpoints.py          # Full CRUD for /dashboards
└── README.md                            # This file
```

**Total:** 8 test files covering 23 API endpoints with 90+ test cases

---

## 🚀 Running Tests

### Prerequisites

**Required environment variables:**
```bash
export OPENAI_API_KEY="your-openai-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
```

**BigQuery credentials** (one of):
- `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json`, OR
- Run `gcloud auth application-default login`

**FAISS indices must exist:**
- Location: `rag_app/faiss_indices/index_sample_queries_with_metadata_recovered/`
- Generate with: `python standalone_embedding_generator.py --csv sample_queries_with_metadata.csv`

### Run All API Tests

```bash
# From project root
cd /Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG

# Run all API tests
pytest tests/api/ -v -m api

# With detailed output
pytest tests/api/ -v -s -m api
```

### Run Specific Test Categories

```bash
# Health checks only (fast, no LLM)
pytest tests/api/test_health_endpoints.py -v

# Query endpoints (slow, LLM calls)
pytest tests/api/test_query_endpoints.py -v

# SQL execution (slow, BigQuery)
pytest tests/api/test_sql_execution_endpoints.py -v -m bigquery

# SQL assistant (slow, many LLM calls)
pytest tests/api/test_sql_assistant_endpoints.py -v

# Schema endpoints
pytest tests/api/test_schema_endpoints.py -v

# Saved queries (Firestore)
pytest tests/api/test_saved_query_endpoints.py -v -m firestore

# Dashboards (Firestore)
pytest tests/api/test_dashboard_endpoints.py -v -m firestore
```

### Run by Test Markers

```bash
# All API tests
pytest -m api

# Only slow tests (LLM API calls)
pytest tests/api/ -m "api and slow"

# Only fast tests (no LLM)
pytest tests/api/ -m "api and not slow"

# Only BigQuery tests
pytest tests/api/ -m bigquery

# Only Firestore tests
pytest tests/api/ -m firestore
```

---

## 🏷️ Test Markers

Tests use these pytest markers:

| Marker | Description | Example |
|--------|-------------|---------|
| `@pytest.mark.api` | API endpoint test (all tests have this) | All tests |
| `@pytest.mark.slow` | Makes real LLM API calls (2-5s each) | Query, SQL assistant tests |
| `@pytest.mark.bigquery` | Requires BigQuery credentials | SQL execution tests |
| `@pytest.mark.firestore` | Requires Firestore access | Saved queries, dashboards |

---

## 🧪 Test Execution Time

| Test File | Test Count | Estimated Time | Why |
|-----------|-----------|----------------|-----|
| test_health_endpoints.py | 6 | ~5-10s | Firestore reads, fast |
| test_query_endpoints.py | 21 | ~60-90s | Real LLM calls (slow) |
| test_sql_execution_endpoints.py | 12 | ~30-60s | Real BigQuery execution |
| test_sql_assistant_endpoints.py | 24 | ~90-120s | Many LLM calls (slow) |
| test_schema_endpoints.py | 11 | ~30-40s | Some LLM calls |
| test_saved_query_endpoints.py | 10 | ~10-20s | Firestore CRUD |
| test_dashboard_endpoints.py | 17 | ~15-30s | Firestore CRUD |
| **TOTAL** | **~100** | **~4-6 minutes** | All tests |

**Fast subset** (no LLM): ~30-60 seconds
**Full suite** (with LLM): ~4-6 minutes

---

## 🧰 Key Fixtures

### Core Fixtures (from `conftest.py`)

**`api_client`** - FastAPI TestClient
```python
def test_example(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
```

**`create_test_saved_query`** - Factory to create saved queries
```python
def test_example(create_test_saved_query):
    query_id = create_test_saved_query()
    # Query auto-deleted after test
```

**`create_test_dashboard`** - Factory to create dashboards
```python
def test_example(create_test_dashboard):
    dashboard_id = create_test_dashboard()
    # Dashboard auto-deleted after test
```

**`cleanup_test_saved_queries`** - Track queries for cleanup
```python
def test_example(api_client, cleanup_test_saved_queries):
    response = api_client.post("/saved_queries", json=data)
    query_id = response.json()["id"]
    cleanup_test_saved_queries.add(query_id)
    # Auto-deleted after test
```

**`cleanup_test_dashboards`** - Track dashboards for cleanup
```python
def test_example(api_client, cleanup_test_dashboards):
    response = api_client.post("/dashboards", json=data)
    dashboard_id = response.json()["id"]
    cleanup_test_dashboards.add(dashboard_id)
    # Auto-deleted after test
```

---

## ✅ Test Coverage Summary

### Endpoints Tested: 23/23 (100%)

**✅ Health (2/2)**
- GET /health
- GET /health/dashboard

**✅ Query (2/2)**
- POST /query/search
- POST /query/quick

**✅ SQL Execution (1/1)**
- POST /sql/execute

**✅ SQL Assistant (5/5)**
- POST /sql/explain
- POST /sql/complete
- POST /sql/fix
- POST /sql/format
- POST /sql/chat

**✅ Schema (3/3)**
- GET /schema/tables
- GET /schema/tables/{table_name}/columns
- GET /schema/tables/{table_name}/description

**✅ Saved Queries (3/3)**
- POST /saved_queries
- GET /saved_queries
- GET /saved_queries/{id}

**✅ Dashboards (7/7)**
- POST /dashboards
- GET /dashboards
- GET /dashboards/{id}
- PATCH /dashboards/{id}
- POST /dashboards/{id}/duplicate
- DELETE /dashboards/{id}

---

## 🎓 Writing New API Tests

### Test Structure Template

```python
@pytest.mark.api
@pytest.mark.slow  # If uses LLM
class TestYourEndpoint:
    """Test suite for POST /your/endpoint"""

    def test_basic_success_case(self, api_client, api_test_logger):
        """Test basic successful request"""
        api_test_logger.info("Testing POST /your/endpoint")

        payload = {"key": "value"}
        response = api_client.post("/your/endpoint", json=payload)

        # Validate HTTP response
        assert response.status_code == 200

        data = response.json()
        assert "expected_field" in data
        assert data["expected_field"] == "expected_value"

    def test_validation_error_case(self, api_client):
        """Test validation error (422)"""
        payload = {"invalid": "data"}
        response = api_client.post("/your/endpoint", json=payload)

        assert response.status_code == 422

    def test_not_found_case(self, api_client):
        """Test 404 error"""
        response = api_client.get("/your/endpoint/nonexistent-id")
        assert response.status_code == 404
```

### Best Practices

1. **Use cleanup fixtures** - Always clean up test data (saved queries, dashboards)
2. **Test HTTP layer** - Focus on request/response, not internal logic
3. **Test status codes** - 200, 201, 404, 422, 503
4. **Test validation** - Invalid input should return 422
5. **Test error cases** - Missing resources should return 404
6. **Use markers** - `@pytest.mark.api`, `@pytest.mark.slow`, etc.
7. **Log important info** - Use `api_test_logger` for debugging

---

## 🐛 Debugging

### View detailed test output

```bash
pytest tests/api/test_query_endpoints.py -v -s
```

### Run single test

```bash
pytest tests/api/test_query_endpoints.py::TestQuerySearchEndpoint::test_simple_product_query_returns_sql -v
```

### Check test prerequisites

```bash
# Verify API keys
echo $OPENAI_API_KEY
echo $GEMINI_API_KEY

# Verify BigQuery auth
gcloud auth application-default print-access-token

# Verify FAISS indices exist
ls -la rag_app/faiss_indices/
```

---

## 📊 Differences from Other Tests

| Feature | Unit Tests (e2e/) | Integration Tests | API Tests (this dir) |
|---------|-------------------|-------------------|----------------------|
| **Test Target** | Python functions | RAG pipeline | HTTP endpoints |
| **HTTP Layer** | No | No | **Yes** |
| **Test Client** | Direct calls | Direct calls | **TestClient (HTTP)** |
| **Mocks** | Everything | Nothing | Nothing |
| **What's Tested** | Code logic | Backend pipeline | **API layer** |
| **Time** | 10-30s | 5-10min | **4-6min** |
| **Use Case** | Dev speed | Pipeline validation | **API validation** |

---

## 🎯 When to Use These Tests

**Use API tests when:**
- ✅ Testing FastAPI endpoint behavior
- ✅ Validating request/response format
- ✅ Testing HTTP status codes
- ✅ Validating Pydantic models
- ✅ Testing error handling
- ✅ Ensuring API contract is maintained

**Use integration tests when:**
- ✅ Testing RAG pipeline logic
- ✅ Validating LLM output quality
- ✅ Testing complex multi-step workflows

**Use unit tests when:**
- ✅ Testing individual functions
- ✅ Fast feedback during development
- ✅ Testing error conditions

---

## 🔗 Related Documentation

- **Integration Tests**: `tests/integration/README.md` (if exists)
- **Unit Tests**: `tests/e2e/` - Mocked unit tests
- **API Documentation**: http://localhost:8080/docs (FastAPI Swagger UI)
- **Deployment Guide**: `rag_app/DEPLOYMENT.md`
- **Project Overview**: `FILE_INDEX.md`

---

**Need help?** Check the test files for examples or run `pytest tests/api/ --collect-only` to see all available tests.
