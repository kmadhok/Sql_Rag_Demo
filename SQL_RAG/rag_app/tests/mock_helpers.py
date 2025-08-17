"""
Mock helpers for testing Streamlit applications and SQL RAG components
"""
from unittest.mock import Mock, MagicMock, patch
from contextlib import contextmanager
import pandas as pd


class MockStreamlitComponents:
    """Helper class to mock Streamlit components for testing"""
    
    def __init__(self):
        self.mock_st = MagicMock()
        self._setup_basic_components()
        self._setup_input_components()
        self._setup_layout_components()
        self._setup_display_components()
        self._setup_session_state()
    
    def _setup_basic_components(self):
        """Setup basic text and message components"""
        self.mock_st.title = Mock()
        self.mock_st.header = Mock()
        self.mock_st.subheader = Mock()
        self.mock_st.write = Mock()
        self.mock_st.caption = Mock()
        self.mock_st.markdown = Mock()
        self.mock_st.code = Mock()
        self.mock_st.divider = Mock()
        
        # Messages
        self.mock_st.info = Mock()
        self.mock_st.warning = Mock()
        self.mock_st.error = Mock()
        self.mock_st.success = Mock()
        self.mock_st.stop = Mock()
    
    def _setup_input_components(self):
        """Setup input components with configurable return values"""
        self.mock_st.text_input = Mock(return_value='')
        self.mock_st.selectbox = Mock(return_value='option1')
        self.mock_st.slider = Mock(return_value=5)
        self.mock_st.checkbox = Mock(return_value=False)
        self.mock_st.button = Mock(return_value=False)
        self.mock_st.radio = Mock(return_value='option1')
        self.mock_st.multiselect = Mock(return_value=[])
    
    def _setup_layout_components(self):
        """Setup layout components"""
        # Columns return mock objects that can be used as context managers
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        
        self.mock_st.columns = Mock(return_value=[mock_col1, mock_col2])
        
        # Container and expander
        mock_container = MagicMock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)
        self.mock_st.container = Mock(return_value=mock_container)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = Mock(return_value=mock_expander)
        mock_expander.__exit__ = Mock(return_value=None)
        self.mock_st.expander = Mock(return_value=mock_expander)
        
        # Spinner
        mock_spinner = MagicMock()
        mock_spinner.__enter__ = Mock(return_value=mock_spinner)
        mock_spinner.__exit__ = Mock(return_value=None)
        self.mock_st.spinner = Mock(return_value=mock_spinner)
    
    def _setup_display_components(self):
        """Setup display components"""
        self.mock_st.metric = Mock()
        self.mock_st.progress = Mock()
        self.mock_st.dataframe = Mock()
        self.mock_st.table = Mock()
        self.mock_st.image = Mock()
        self.mock_st.plotly_chart = Mock()
    
    def _setup_session_state(self):
        """Setup session state mock"""
        self.mock_st.session_state = {}
    
    def configure_input(self, component_name: str, return_value):
        """Configure return value for input components"""
        getattr(self.mock_st, component_name).return_value = return_value
    
    def configure_session_state(self, state_dict: dict):
        """Configure session state with given dictionary"""
        self.mock_st.session_state.update(state_dict)
    
    def get_mock(self):
        """Get the configured mock streamlit object"""
        return self.mock_st


class MockDocuments:
    """Helper to create mock document objects for testing"""
    
    @staticmethod
    def create_document(content: str, metadata: dict = None):
        """Create a mock document with content and metadata"""
        mock_doc = Mock()
        mock_doc.page_content = content
        mock_doc.metadata = metadata or {}
        return mock_doc
    
    @staticmethod
    def create_documents_list(contents: list, metadatas: list = None):
        """Create a list of mock documents"""
        if metadatas is None:
            metadatas = [{}] * len(contents)
        
        return [
            MockDocuments.create_document(content, metadata)
            for content, metadata in zip(contents, metadatas)
        ]


class MockSessionManager:
    """Mock session manager for testing"""
    
    def __init__(self, csv_data=None, vector_store=None):
        self.mock = Mock()
        self._csv_data = csv_data
        self._vector_store = vector_store
        self._setup_methods()
    
    def _setup_methods(self):
        """Setup mock methods with realistic behavior"""
        self.mock.load_csv_data_if_needed = Mock(return_value=True)
        self.mock.get_csv_data = Mock(return_value=self._csv_data)
        self.mock.get_vector_store = Mock(return_value=self._vector_store)
        self.mock.get_schema_manager = Mock(return_value=None)
        self.mock.load_schema_manager_if_needed = Mock()
        self.mock.load_schema_agent_if_needed = Mock()
        self.mock.display_session_stats = Mock()
        self.mock.add_token_usage = Mock()
        self.mock.add_chat_message = Mock()
        self.mock.get_conversation_context = Mock(return_value=[])
    
    def set_csv_data(self, data):
        """Set CSV data for testing"""
        self._csv_data = data
        self.mock.get_csv_data.return_value = data
    
    def set_vector_store(self, vector_store):
        """Set vector store for testing"""
        self._vector_store = vector_store
        self.mock.get_vector_store.return_value = vector_store
    
    def get_mock(self):
        """Get the configured mock session manager"""
        return self.mock


class MockVectorStoreManager:
    """Mock vector store manager for testing"""
    
    def __init__(self, available_indices=None):
        self.mock = Mock()
        self._available_indices = available_indices or ['index1', 'index2']
        self._setup_methods()
    
    def _setup_methods(self):
        """Setup mock methods"""
        self.mock.get_available_indices = Mock(return_value=self._available_indices)
        self.mock.ensure_vector_store_loaded = Mock(return_value=True)
        self.mock.load_vector_store_if_needed = Mock(return_value=True)
    
    def set_available_indices(self, indices):
        """Set available indices for testing"""
        self._available_indices = indices
        self.mock.get_available_indices.return_value = indices
    
    def get_mock(self):
        """Get the configured mock vector store manager"""
        return self.mock


class MockRAGEngine:
    """Mock RAG engine for testing"""
    
    def __init__(self):
        self.mock = Mock()
        self._setup_methods()
    
    def _setup_methods(self):
        """Setup mock methods with realistic return values"""
        self.mock.answer_question = Mock(return_value=(
            "Sample answer from RAG engine",
            MockDocuments.create_documents_list([
                "Sample document content 1",
                "Sample document content 2"
            ]),
            {
                'total_tokens': 150,
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'retrieval_time': 0.5,
                'documents_processed': 2
            }
        ))
    
    def configure_answer(self, answer: str, sources: list = None, token_usage: dict = None):
        """Configure the answer returned by the RAG engine"""
        if sources is None:
            sources = MockDocuments.create_documents_list(["Default source content"])
        if token_usage is None:
            token_usage = {'total_tokens': 100, 'prompt_tokens': 80, 'completion_tokens': 20}
        
        self.mock.answer_question.return_value = (answer, sources, token_usage)
    
    def get_mock(self):
        """Get the configured mock RAG engine"""
        return self.mock


@contextmanager
def mock_streamlit_app():
    """Context manager to mock the entire streamlit module"""
    mock_components = MockStreamlitComponents()
    
    with patch('streamlit', mock_components.get_mock()):
        yield mock_components.get_mock()


@contextmanager 
def mock_page_dependencies():
    """Context manager to mock all common page dependencies"""
    mock_st = MockStreamlitComponents()
    mock_session_manager = MockSessionManager()
    mock_vector_manager = MockVectorStoreManager()
    mock_rag_engine = MockRAGEngine()
    
    with patch.multiple(
        'modular.page_modules.search_page',
        st=mock_st.get_mock(),
        session_manager=mock_session_manager.get_mock(),
        vector_store_manager=mock_vector_manager.get_mock(),
        rag_engine=mock_rag_engine.get_mock()
    ):
        yield {
            'streamlit': mock_st.get_mock(),
            'session_manager': mock_session_manager.get_mock(),
            'vector_store_manager': mock_vector_manager.get_mock(),
            'rag_engine': mock_rag_engine.get_mock()
        }


def create_sample_dataframe(num_rows: int = 5) -> pd.DataFrame:
    """Create a sample DataFrame for testing"""
    return pd.DataFrame({
        'query': [f'SELECT * FROM table_{i}' for i in range(num_rows)],
        'description': [f'Description for query {i}' for i in range(num_rows)],
        'tables': [f'table_{i}' for i in range(num_rows)],
        'joins': [f'join_{i}' if i % 2 == 0 else '' for i in range(num_rows)],
        'tables_parsed': [[f'table_{i}'] for i in range(num_rows)],
        'joins_parsed': [
            [{'left_table': f'table_{i}', 'right_table': f'table_{i+1}', 'join_type': 'INNER'}] if i % 2 == 0 else []
            for i in range(num_rows)
        ]
    })


def create_sample_analytics() -> dict:
    """Create sample analytics data for testing"""
    return {
        'total_queries': 100,
        'queries_with_descriptions': 95,
        'queries_with_tables': 85,
        'queries_with_joins': 45,
        'total_individual_joins': 120,
        'max_joins_per_query': 5,
        'join_count_distribution': {0: 55, 1: 25, 2: 15, 3: 5},
        'json_format_count': 80,
        'string_format_count': 40,
        'join_types': {'INNER JOIN': 60, 'LEFT JOIN': 35, 'RIGHT JOIN': 15, 'FULL JOIN': 10},
        'table_usage': {'customers': 45, 'orders': 40, 'products': 35},
        'relationships': [
            {
                'left_table': 'customers',
                'right_table': 'orders',
                'join_type': 'INNER JOIN',
                'condition': 'customers.id = orders.customer_id'
            }
        ]
    }