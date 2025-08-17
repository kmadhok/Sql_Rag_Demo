"""
Pytest configuration and fixtures for SQL RAG tests
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, MagicMock
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_query_data():
    """Sample CSV data for testing"""
    return pd.DataFrame({
        'query': [
            'SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id',
            'SELECT p.name, c.category FROM products p JOIN categories c ON p.category_id = c.id',
            'SELECT * FROM customers WHERE city = "New York"'
        ],
        'description': [
            'Calculate total order amount per customer',
            'Get product names with categories using JOIN',
            'Find all customers in New York'
        ],
        'tables': [
            'orders',
            'products,categories',
            'customers'
        ],
        'joins': [
            '',
            'products.category_id = categories.id',
            ''
        ]
    })


@pytest.fixture
def sample_query_data_with_parsed():
    """Sample CSV data with pre-parsed columns for testing"""
    return pd.DataFrame({
        'query': [
            'SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id',
            'SELECT p.name, c.category FROM products p JOIN categories c ON p.category_id = c.id'
        ],
        'description': [
            'Calculate total order amount per customer',
            'Get product names with categories using JOIN'
        ],
        'tables': [
            'orders',
            'products,categories'
        ],
        'joins': [
            '',
            'products.category_id = categories.id'
        ],
        'tables_parsed': [
            ['orders'],
            ['products', 'categories']
        ],
        'joins_parsed': [
            [],
            [{'left_table': 'products', 'right_table': 'categories', 'join_type': 'INNER JOIN'}]
        ]
    })


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit components for testing"""
    mock_st = MagicMock()
    
    # Mock common Streamlit functions
    mock_st.title = Mock()
    mock_st.header = Mock()
    mock_st.subheader = Mock()
    mock_st.write = Mock()
    mock_st.caption = Mock()
    mock_st.info = Mock()
    mock_st.warning = Mock()
    mock_st.error = Mock()
    mock_st.success = Mock()
    mock_st.code = Mock()
    mock_st.divider = Mock()
    mock_st.stop = Mock()
    
    # Mock input components
    mock_st.text_input = Mock(return_value='')
    mock_st.selectbox = Mock(return_value='option1')
    mock_st.slider = Mock(return_value=5)
    mock_st.checkbox = Mock(return_value=False)
    mock_st.button = Mock(return_value=False)
    
    # Mock layout components
    mock_st.columns = Mock(return_value=[Mock(), Mock()])
    mock_st.container = Mock()
    mock_st.expander = Mock()
    mock_st.spinner = Mock()
    
    # Mock metrics and display
    mock_st.metric = Mock()
    mock_st.progress = Mock()
    mock_st.dataframe = Mock()
    
    # Mock session state
    mock_st.session_state = {}
    
    return mock_st


@pytest.fixture
def mock_session_manager():
    """Mock session manager for testing"""
    mock_manager = Mock()
    mock_manager.load_csv_data_if_needed = Mock(return_value=True)
    mock_manager.get_csv_data = Mock()
    mock_manager.get_vector_store = Mock()
    mock_manager.get_schema_manager = Mock(return_value=None)
    mock_manager.load_schema_manager_if_needed = Mock()
    mock_manager.load_schema_agent_if_needed = Mock()
    mock_manager.display_session_stats = Mock()
    mock_manager.add_token_usage = Mock()
    mock_manager.add_chat_message = Mock()
    mock_manager.get_conversation_context = Mock(return_value=[])
    return mock_manager


@pytest.fixture
def mock_vector_store_manager():
    """Mock vector store manager for testing"""
    mock_manager = Mock()
    mock_manager.get_available_indices = Mock(return_value=['index1', 'index2'])
    mock_manager.ensure_vector_store_loaded = Mock(return_value=True)
    mock_manager.load_vector_store_if_needed = Mock(return_value=True)
    return mock_manager


@pytest.fixture
def mock_rag_engine():
    """Mock RAG engine for testing"""
    mock_engine = Mock()
    mock_engine.answer_question = Mock(return_value=(
        "Sample answer",
        [Mock(page_content="Sample content", metadata={'source': 'test'})],
        {'total_tokens': 100, 'prompt_tokens': 80, 'completion_tokens': 20}
    ))
    return mock_engine