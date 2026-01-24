# End-to-End Testing Suite for SQL RAG Application

Comprehensive test suite for `app_simple_gemini.py` covering complete user workflows and feature interactions.

## 📋 Test Coverage

### 1. Chat Conversation Flow (`test_chat_conversation_flow.py`)
- User input processing and agent detection
- RAG retrieval and LLM response generation
- Message history and conversation context
- Token tracking and utilization
- Multi-turn conversations
- Error handling and timeouts

### 2. SQL Generation & Execution (`test_sql_generation_and_execution.py`)
- SQL extraction from LLM responses
- SQL safety validation (blocking DELETE, DROP, UPDATE, etc.)
- BigQuery query execution
- Result display and formatting
- Dry run and cost estimation
- Cache hit detection

### 3. Catalog Browsing Flow (`test_catalog_browsing_flow.py`)
- CSV/Parquet data loading
- Search and filtering
- Pagination for large datasets
- Query card display
- Join analysis display
- Analytics caching

### 4. Agent Workflows (`test_agent_workflows.py`)
- `@explain` - Detailed explanations
- `@create` - SQL generation
- `@schema` - LookML exploration
- `@longanswer` - Comprehensive responses
- Agent-specific prompt templates
- Direct schema responses

## 🚀 Quick Start

### Install Test Dependencies

```bash
pip install pytest pytest-mock
```

### Run All Tests

```bash
# From project root
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=rag_app --cov-report=term-missing
```

### Run Specific Test Categories

```bash
# Chat tests only
pytest -m chat

# SQL tests only
pytest -m sql

# Catalog tests only
pytest -m catalog

# Agent tests only
pytest -m agent

# All e2e tests
pytest -m e2e
```

### Run Specific Test Files

```bash
# Chat conversation tests
pytest tests/e2e/test_chat_conversation_flow.py

# SQL execution tests
pytest tests/e2e/test_sql_generation_and_execution.py

# Catalog browsing tests
pytest tests/e2e/test_catalog_browsing_flow.py

# Agent workflow tests
pytest tests/e2e/test_agent_workflows.py
```

### Run Specific Test Functions

```bash
# Run a specific test
pytest tests/e2e/test_chat_conversation_flow.py::TestChatConversationFlow::test_simple_question_answer_flow

# Run all tests in a class
pytest tests/e2e/test_agent_workflows.py::TestAgentWorkflows
```

## 📊 Test Markers

Tests are organized with pytest markers for easy filtering:

- `@pytest.mark.e2e` - End-to-end integration tests
- `@pytest.mark.chat` - Chat conversation tests
- `@pytest.mark.sql` - SQL generation/execution tests
- `@pytest.mark.catalog` - Catalog browsing tests
- `@pytest.mark.agent` - Agent workflow tests
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.mock` - Tests using mocked dependencies

## 🧪 Test Fixtures

### Shared Fixtures (in `conftest.py`)
- `mock_vector_store` - Mock FAISS vector store
- `mock_csv_data` - Sample query data
- `mock_gemini_client` - Mock LLM client
- `mock_bigquery_executor` - Mock BigQuery executor
- `mock_schema_manager` - Mock schema manager
- `mock_conversation_manager` - Mock conversation storage
- `mock_lookml_safe_join_map` - Mock LookML data
- `sample_chat_messages` - Sample conversation
- `sample_sql_query` - Sample SQL query
- `sample_sql_response` - Sample LLM response with SQL

### Mock Helpers (in `fixtures/mock_helpers.py`)
Factory functions for creating test data:
- `create_mock_csv_data()` - Generate mock query data
- `create_mock_documents()` - Generate mock vector store documents
- `create_mock_lookml_safe_join_map()` - Generate mock LookML data

## 📁 Test Structure

```
tests/
├── README.md                          # This file
├── fixtures/
│   ├── mock_helpers.py                # Mock factory functions
│   └── sample_test_queries.csv        # Sample test data (15 queries)
└── e2e/
    ├── conftest.py                    # Shared fixtures
    ├── test_chat_conversation_flow.py # Chat tests (13 tests)
    ├── test_sql_generation_and_execution.py # SQL tests (20 tests)
    ├── test_catalog_browsing_flow.py  # Catalog tests (18 tests)
    └── test_agent_workflows.py        # Agent tests (19 tests)

Total: 70+ end-to-end tests
```

## ⚙️ Configuration

Test configuration is in `pytest.ini` at project root:
- Test discovery patterns
- Marker definitions
- Output formatting
- Warning filters

## 🔍 Writing New Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test Structure

```python
import pytest
from unittest.mock import patch

@pytest.mark.e2e
@pytest.mark.chat
class TestNewFeature:
    """Test suite for new feature"""

    def test_basic_functionality(self, mock_vector_store):
        """Test basic feature behavior"""
        # Arrange
        input_data = "test input"

        # Act
        result = some_function(input_data)

        # Assert
        assert result is not None
        assert expected_value in result
```

### Using Fixtures

```python
def test_with_fixtures(
    mock_vector_store,
    mock_gemini_client,
    mock_schema_manager
):
    """Fixtures are automatically injected"""
    result = answer_question_chat_mode(
        question="test",
        vector_store=mock_vector_store,
        schema_manager=mock_schema_manager
    )
    assert result is not None
```

## 🐛 Debugging Tests

### Run with debugging output

```bash
# Show print statements
pytest -s

# Show detailed failure info
pytest -vv

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb
```

### View captured logs

```bash
# Show log output
pytest --log-cli-level=INFO

# Show all logs including debug
pytest --log-cli-level=DEBUG
```

## 📈 Test Coverage

Generate coverage reports:

```bash
# Terminal report
pytest --cov=rag_app --cov-report=term

# HTML report (creates htmlcov/ directory)
pytest --cov=rag_app --cov-report=html

# Open HTML report
open htmlcov/index.html
```

## ✅ Test Best Practices

1. **Use descriptive test names** - Test name should explain what is being tested
2. **One assertion per concept** - Each test should verify one behavior
3. **Arrange-Act-Assert pattern** - Structure tests clearly
4. **Use fixtures** - Share setup code via pytest fixtures
5. **Mock external dependencies** - Don't hit real APIs or databases
6. **Test edge cases** - Empty inputs, large inputs, invalid inputs
7. **Keep tests fast** - Use mocks to avoid slow operations

## 🔧 Troubleshooting

### Import Errors
If you see import errors, ensure the project root is in your Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/SQL_RAG/rag_app"
```

### Fixture Not Found
Make sure `conftest.py` is in the correct location and pytest can discover it.

### Mock Not Working
Verify you're patching the correct module path where the function is used, not where it's defined.

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-mock Plugin](https://pytest-mock.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

## 🎯 Future Enhancements

Potential test additions:
- Performance benchmarking tests
- Load testing for concurrent users
- Integration tests with real BigQuery (requires credentials)
- Visual regression tests for UI components
- Property-based testing with Hypothesis
