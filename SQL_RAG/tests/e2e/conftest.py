#!/usr/bin/env python3
"""
Shared pytest fixtures for end-to-end tests
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "rag_app"))

# Import mock helpers
from tests.fixtures.mock_helpers import (
    MockDocument,
    MockVectorStore,
    MockGeminiClient,
    MockBigQueryExecutor,
    MockSchemaManager,
    MockConversationManager,
    create_mock_csv_data,
    create_mock_documents,
    create_mock_lookml_safe_join_map
)


@pytest.fixture
def mock_vector_store():
    """Fixture providing a mock FAISS vector store"""
    documents = create_mock_documents(num_docs=10)
    return MockVectorStore(documents)


@pytest.fixture
def mock_csv_data():
    """Fixture providing mock CSV data"""
    return create_mock_csv_data(num_queries=15)


@pytest.fixture
def mock_gemini_client():
    """Fixture providing a mock Gemini client"""
    responses = [
        "Here's a SQL query to find users:\n```sql\nSELECT * FROM users WHERE created_at > '2023-01-01'\n```",
        "This query retrieves user information from the database.",
        "To optimize this query, consider adding an index on the created_at column."
    ]
    return MockGeminiClient(responses=responses)


@pytest.fixture
def mock_bigquery_executor():
    """Fixture providing a mock BigQuery executor"""
    return MockBigQueryExecutor()


@pytest.fixture
def mock_schema_manager():
    """Fixture providing a mock schema manager"""
    schema_data = pd.DataFrame({
        'table_id': [
            'users', 'users', 'users',
            'orders', 'orders', 'orders',
            'products', 'products'
        ],
        'column': [
            'user_id', 'name', 'email',
            'order_id', 'user_id', 'total',
            'product_id', 'name'
        ],
        'datatype': [
            'INT64', 'STRING', 'STRING',
            'INT64', 'INT64', 'FLOAT64',
            'INT64', 'STRING'
        ]
    })
    return MockSchemaManager(schema_data=schema_data)


@pytest.fixture
def mock_conversation_manager():
    """Fixture providing a mock conversation manager"""
    return MockConversationManager()


@pytest.fixture
def mock_lookml_safe_join_map():
    """Fixture providing a mock LookML safe-join map"""
    return create_mock_lookml_safe_join_map()


@pytest.fixture
def mock_streamlit_session_state():
    """Fixture providing a mock Streamlit session state"""
    return {
        'chat_messages': [],
        'token_usage': [],
        'csv_data': create_mock_csv_data(num_queries=15),
        'schema_manager': None,
        'lookml_safe_join_map': None,
        'advanced_mode': False,
        'user_context': '',
        'excluded_tables': []
    }


@pytest.fixture
def mock_streamlit():
    """Fixture providing mocked Streamlit components"""
    with patch('streamlit.session_state', new_callable=dict) as mock_st_state, \
         patch('streamlit.title') as mock_title, \
         patch('streamlit.caption') as mock_caption, \
         patch('streamlit.chat_message') as mock_chat_message, \
         patch('streamlit.chat_input') as mock_chat_input, \
         patch('streamlit.spinner') as mock_spinner, \
         patch('streamlit.error') as mock_error, \
         patch('streamlit.success') as mock_success, \
         patch('streamlit.warning') as mock_warning, \
         patch('streamlit.info') as mock_info:

        # Initialize session state with default values
        mock_st_state.update({
            'chat_messages': [],
            'token_usage': [],
            'advanced_mode': False,
            'user_context': '',
            'excluded_tables': []
        })

        yield {
            'session_state': mock_st_state,
            'title': mock_title,
            'caption': mock_caption,
            'chat_message': mock_chat_message,
            'chat_input': mock_chat_input,
            'spinner': mock_spinner,
            'error': mock_error,
            'success': mock_success,
            'warning': mock_warning,
            'info': mock_info
        }


@pytest.fixture
def sample_chat_messages():
    """Fixture providing sample chat messages"""
    return [
        {
            'role': 'user',
            'content': 'Show me all users',
            'agent_type': None,
            'actual_question': 'Show me all users'
        },
        {
            'role': 'assistant',
            'content': 'Here is a query:\n```sql\nSELECT * FROM users\n```',
            'sources': create_mock_documents(num_docs=3),
            'token_usage': {'total_tokens': 100, 'prompt_tokens': 50, 'completion_tokens': 50},
            'agent_type': None
        }
    ]


@pytest.fixture
def sample_sql_query():
    """Fixture providing a sample SQL query"""
    return "SELECT user_id, name, email FROM users WHERE created_at > '2023-01-01' LIMIT 100"


@pytest.fixture
def sample_sql_response():
    """Fixture providing a sample SQL response with embedded query"""
    return """Here's a query to retrieve recent users:

```sql
SELECT user_id, name, email, created_at
FROM `bigquery-public-data.thelook_ecommerce.users`
WHERE created_at > '2023-01-01'
ORDER BY created_at DESC
LIMIT 100
```

This query will return the 100 most recent users created after January 1, 2023.
"""


@pytest.fixture
def test_data_dir():
    """Fixture providing the test data directory path"""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mock_environment_variables(monkeypatch):
    """Fixture for setting test environment variables"""
    monkeypatch.setenv('GEMINI_API_KEY', 'test_api_key')
    monkeypatch.setenv('BIGQUERY_PROJECT_ID', 'test-project')
    monkeypatch.setenv('BIGQUERY_DATASET', 'test_dataset')
    monkeypatch.setenv('EMBEDDING_TIMEOUT_SECONDS', '10')
    monkeypatch.setenv('CHAT_SCHEMA_DOC_LIMIT', '25')


@pytest.fixture(autouse=True)
def reset_module_cache():
    """Auto-used fixture to reset module imports between tests"""
    yield
    # Clean up any cached imports if needed
    modules_to_remove = [
        mod for mod in sys.modules
        if mod.startswith('rag_app.') or mod.startswith('tests.')
    ]
    for mod in modules_to_remove:
        if mod in sys.modules:
            del sys.modules[mod]


@pytest.fixture
def captured_logs(caplog):
    """Fixture for capturing logs during tests"""
    import logging
    caplog.set_level(logging.INFO)
    return caplog
