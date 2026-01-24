#!/usr/bin/env python3
"""
Mock Helpers for Testing
Provides factory functions and utilities for creating test mocks
"""

from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock, Mock
import pandas as pd
from datetime import datetime


class MockDocument:
    """Mock LangChain Document for testing"""

    def __init__(self, page_content: str, metadata: Optional[Dict] = None):
        self.page_content = page_content
        self.metadata = metadata or {}


class MockVectorStore:
    """Mock FAISS vector store for testing"""

    def __init__(self, documents: List[MockDocument]):
        self.documents = documents
        self.docstore = Mock()
        self.docstore._dict = {i: doc for i, doc in enumerate(documents)}

    def similarity_search(self, query: str, k: int = 5) -> List[MockDocument]:
        """Return first k documents (simple mock)"""
        return self.documents[:k]

    def similarity_search_with_score(self, query: str, k: int = 5):
        """Return documents with mock scores"""
        return [(doc, 0.9 - i * 0.1) for i, doc in enumerate(self.documents[:k])]


class MockGeminiClient:
    """Mock Gemini LLM client for testing"""

    def __init__(self, responses: Optional[List[str]] = None):
        self.responses = responses or ["This is a mock SQL response"]
        self.call_count = 0

    def invoke(self, prompt: str) -> str:
        """Return next mock response"""
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response


class MockQueryResult:
    """Mock BigQuery QueryResult for testing"""

    def __init__(
        self,
        success: bool = True,
        data: Optional[pd.DataFrame] = None,
        total_rows: int = 0,
        execution_time: float = 0.5,
        bytes_processed: int = 1024,
        bytes_billed: int = 1024,
        cache_hit: bool = False,
        error_message: str = "",
        job_id: str = "test_job_123",
        dry_run: bool = False
    ):
        self.success = success
        self.data = data if data is not None else pd.DataFrame()
        self.total_rows = total_rows
        self.execution_time = execution_time
        self.bytes_processed = bytes_processed
        self.bytes_billed = bytes_billed
        self.cache_hit = cache_hit
        self.error_message = error_message
        self.job_id = job_id
        self.dry_run = dry_run


class MockBigQueryExecutor:
    """Mock BigQuery executor for testing"""

    def __init__(self, project_id: str = "test-project", dataset_id: str = "test_dataset"):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.max_rows = 1000
        self.timeout_seconds = 30

    def validate_sql_safety(self, sql: str) -> tuple:
        """Mock SQL safety validation"""
        forbidden_keywords = ['DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'INSERT', 'UPDATE']
        sql_upper = sql.upper()

        for keyword in forbidden_keywords:
            if keyword in sql_upper:
                return False, f"Forbidden operation: {keyword}"

        return True, "Query passed safety validation"

    def extract_sql_from_text(self, text: str) -> Optional[str]:
        """Mock SQL extraction from text"""
        # Simple extraction: look for SQL keywords
        if 'SELECT' in text.upper():
            # Find code blocks or return text with SELECT
            if '```sql' in text:
                start = text.find('```sql') + 6
                end = text.find('```', start)
                return text[start:end].strip()
            elif 'SELECT' in text:
                # Return first line with SELECT
                for line in text.split('\n'):
                    if 'SELECT' in line.upper():
                        return line.strip()
        return None

    def execute_query(
        self,
        sql: str,
        dry_run: bool = False,
        max_bytes_billed: int = 100_000_000
    ) -> MockQueryResult:
        """Mock query execution"""
        # Simulate successful execution
        mock_data = pd.DataFrame({
            'user_id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'email': ['alice@example.com', 'bob@example.com', 'charlie@example.com']
        })

        return MockQueryResult(
            success=True,
            data=mock_data,
            total_rows=3,
            execution_time=0.45,
            bytes_processed=2048,
            bytes_billed=0 if dry_run else 2048,
            cache_hit=False,
            dry_run=dry_run
        )


class MockSchemaManager:
    """Mock SchemaManager for testing"""

    def __init__(self, schema_data: Optional[pd.DataFrame] = None):
        self.schema_df = schema_data if schema_data is not None else pd.DataFrame({
            'table_id': ['users', 'orders', 'products'],
            'column': ['user_id', 'order_id', 'product_id'],
            'datatype': ['INT64', 'INT64', 'INT64']
        })
        self.table_count = len(self.schema_df['table_id'].unique())
        self.column_count = len(self.schema_df)
        self.schema_lookup = self._build_lookup()

    def _build_lookup(self) -> Dict[str, List[str]]:
        """Build table -> columns lookup"""
        lookup = {}
        for table in self.schema_df['table_id'].unique():
            lookup[table] = self.schema_df[self.schema_df['table_id'] == table]['column'].tolist()
        return lookup

    def _normalize_table_name(self, table: str) -> str:
        """Normalize table name"""
        return table.lower().split('.')[-1]

    def get_relevant_schema(self, tables: List[str], max_tables: int = 10) -> str:
        """Mock schema generation"""
        if not tables:
            return ""

        schema_text = "Database Schema:\n"
        for table in tables[:max_tables]:
            norm_table = self._normalize_table_name(table)
            if norm_table in self.schema_lookup:
                columns = self.schema_lookup[norm_table]
                schema_text += f"\nTable: {norm_table}\n"
                schema_text += f"Columns: {', '.join(columns)}\n"

        return schema_text

    def get_fqn_map(self, tables: List[str]) -> Dict[str, str]:
        """Mock FQN mapping"""
        return {
            table: f"bigquery-public-data.thelook_ecommerce.{self._normalize_table_name(table)}"
            for table in tables
        }

    def get_table_columns(self, table: str) -> List[str]:
        """Get columns for a table"""
        norm_table = self._normalize_table_name(table)
        return self.schema_lookup.get(norm_table, [])

    def get_fqn(self, table: str) -> Optional[str]:
        """Get fully qualified name for a table"""
        norm_table = self._normalize_table_name(table)
        if norm_table in self.schema_lookup:
            return f"bigquery-public-data.thelook_ecommerce.{norm_table}"
        return None


class MockConversationManager:
    """Mock conversation manager for testing"""

    def __init__(self):
        self.conversations = {}
        self.firestore_available = False

    def save_conversation(
        self,
        messages: List[Dict],
        user_session_id: str,
        conversation_id: Optional[str] = None
    ) -> tuple:
        """Mock save conversation"""
        conv_id = conversation_id or f"conv_{len(self.conversations) + 1}"
        self.conversations[conv_id] = {
            'messages': messages,
            'user_session_id': user_session_id,
            'updated_at': datetime.now()
        }
        return conv_id, True

    def load_conversation(self, conversation_id: str, user_session_id: str) -> Optional[Dict]:
        """Mock load conversation"""
        return self.conversations.get(conversation_id)

    def list_conversations(
        self,
        user_session_id: str,
        limit: int = 20,
        search_term: Optional[str] = None
    ) -> List[Any]:
        """Mock list conversations"""
        return []

    def delete_conversation(self, conversation_id: str, user_session_id: str) -> bool:
        """Mock delete conversation"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False

    def get_storage_status(self) -> Dict[str, Any]:
        """Mock storage status"""
        return {
            'firestore_available': self.firestore_available,
            'fallback_conversations': len(self.conversations)
        }


def create_mock_csv_data(num_queries: int = 10) -> pd.DataFrame:
    """Create mock CSV data for testing"""
    queries = []
    for i in range(num_queries):
        queries.append({
            'query': f'SELECT * FROM users WHERE id = {i}',
            'description': f'Test query {i}',
            'tables': 'users',
            'joins': '',
            'tables_parsed': ['users'],
            'joins_parsed': []
        })
    return pd.DataFrame(queries)


def create_mock_documents(num_docs: int = 5) -> List[MockDocument]:
    """Create mock documents for vector store"""
    docs = []
    for i in range(num_docs):
        content = f"""
Query: SELECT user_id, name, email FROM users WHERE created_at > '2023-01-01'
Description: Get users created after 2023
Tables: users
        """.strip()
        docs.append(MockDocument(content, {'source': f'doc_{i}'}))
    return docs


def create_mock_lookml_safe_join_map() -> Dict[str, Any]:
    """Create mock LookML safe-join map"""
    return {
        'project': 'test_project',
        'explores': {
            'users': {
                'label': 'Users',
                'description': 'User explore',
                'base_table': 'users',
                'joins': {
                    'orders': {
                        'sql_on': '${users.id} = ${orders.user_id}',
                        'relationship': 'one_to_many',
                        'join_type': 'LEFT OUTER'
                    }
                }
            }
        },
        'join_graph': {
            'users': ['orders', 'events'],
            'orders': ['users', 'order_items'],
            'products': ['order_items']
        },
        'metadata': {
            'total_explores': 1,
            'total_joins': 1
        }
    }
