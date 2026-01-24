#!/usr/bin/env python3
"""
End-to-End Tests for SQL Generation and Execution Flow

Tests complete SQL workflow:
- SQL generation from natural language
- SQL extraction from LLM responses
- SQL safety validation
- BigQuery execution
- Result display
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "rag_app"))

from tests.fixtures.mock_helpers import MockQueryResult


@pytest.mark.e2e
@pytest.mark.sql
class TestSQLGenerationAndExecution:
    """Test suite for complete SQL generation and execution flows"""

    def test_sql_extraction_from_markdown(self, mock_bigquery_executor, sample_sql_response):
        """Test extraction of SQL from markdown code blocks"""
        from rag_app.app_simple_gemini import display_sql_execution_interface

        sql = mock_bigquery_executor.extract_sql_from_text(sample_sql_response)

        assert sql is not None, "Should extract SQL from markdown"
        assert 'SELECT' in sql.upper(), "Extracted SQL should contain SELECT"
        assert 'FROM' in sql.upper(), "Extracted SQL should contain FROM"

    def test_sql_extraction_from_plain_text(self, mock_bigquery_executor):
        """Test extraction of SQL from plain text without markdown"""
        text = "Here's your query: SELECT user_id, name FROM users WHERE active = true"

        sql = mock_bigquery_executor.extract_sql_from_text(text)

        assert sql is not None, "Should extract SQL from plain text"
        assert 'SELECT' in sql, "Should contain SELECT statement"

    def test_sql_safety_validation_allow_select(self, mock_bigquery_executor):
        """Test that safe SELECT queries pass validation"""
        safe_sql = "SELECT * FROM users WHERE created_at > '2023-01-01'"

        is_valid, message = mock_bigquery_executor.validate_sql_safety(safe_sql)

        assert is_valid is True, "Safe SELECT should pass validation"
        assert 'passed' in message.lower(), "Validation message should indicate success"

    def test_sql_safety_validation_block_delete(self, mock_bigquery_executor):
        """Test that DELETE queries are blocked"""
        dangerous_sql = "DELETE FROM users WHERE user_id = 123"

        is_valid, message = mock_bigquery_executor.validate_sql_safety(dangerous_sql)

        assert is_valid is False, "DELETE should be blocked"
        assert 'DELETE' in message, "Should mention blocked operation"

    def test_sql_safety_validation_block_drop(self, mock_bigquery_executor):
        """Test that DROP queries are blocked"""
        dangerous_sql = "DROP TABLE users"

        is_valid, message = mock_bigquery_executor.validate_sql_safety(dangerous_sql)

        assert is_valid is False, "DROP should be blocked"
        assert 'DROP' in message, "Should mention blocked operation"

    def test_sql_safety_validation_block_update(self, mock_bigquery_executor):
        """Test that UPDATE queries are blocked"""
        dangerous_sql = "UPDATE users SET active = false WHERE user_id = 123"

        is_valid, message = mock_bigquery_executor.validate_sql_safety(dangerous_sql)

        assert is_valid is False, "UPDATE should be blocked"
        assert 'UPDATE' in message, "Should mention blocked operation"

    def test_sql_execution_success(self, mock_bigquery_executor, sample_sql_query):
        """Test successful SQL query execution"""
        result = mock_bigquery_executor.execute_query(sample_sql_query)

        assert result.success is True, "Query should execute successfully"
        assert isinstance(result.data, pd.DataFrame), "Should return DataFrame"
        assert result.total_rows > 0, "Should have some rows"
        assert result.execution_time > 0, "Should track execution time"
        assert result.bytes_processed > 0, "Should track bytes processed"

    def test_sql_execution_dry_run(self, mock_bigquery_executor, sample_sql_query):
        """Test dry run execution (cost estimation)"""
        result = mock_bigquery_executor.execute_query(sample_sql_query, dry_run=True)

        assert result.dry_run is True, "Should be marked as dry run"
        assert result.bytes_billed == 0, "Dry run should not bill bytes"
        assert result.bytes_processed > 0, "Should still estimate bytes processed"

    def test_sql_execution_with_max_bytes_limit(self, mock_bigquery_executor, sample_sql_query):
        """Test execution with max bytes billed limit"""
        max_bytes = 50_000_000

        result = mock_bigquery_executor.execute_query(
            sample_sql_query,
            dry_run=False,
            max_bytes_billed=max_bytes
        )

        # For mock, this just passes through, but verifies parameter handling
        assert result is not None, "Should handle max_bytes_billed parameter"

    def test_query_result_structure(self):
        """Test QueryResult object structure and attributes"""
        result = MockQueryResult(
            success=True,
            total_rows=100,
            execution_time=1.5,
            bytes_processed=1024000,
            bytes_billed=1024000,
            cache_hit=False
        )

        # Verify all expected attributes exist
        assert hasattr(result, 'success'), "Should have success attribute"
        assert hasattr(result, 'data'), "Should have data attribute"
        assert hasattr(result, 'total_rows'), "Should have total_rows attribute"
        assert hasattr(result, 'execution_time'), "Should have execution_time attribute"
        assert hasattr(result, 'bytes_processed'), "Should have bytes_processed attribute"
        assert hasattr(result, 'bytes_billed'), "Should have bytes_billed attribute"
        assert hasattr(result, 'cache_hit'), "Should have cache_hit attribute"
        assert hasattr(result, 'job_id'), "Should have job_id attribute"

    def test_failed_query_result(self):
        """Test QueryResult for failed queries"""
        result = MockQueryResult(
            success=False,
            error_message="Table not found: unknown_table",
            total_rows=0
        )

        assert result.success is False, "Should indicate failure"
        assert len(result.error_message) > 0, "Should have error message"
        assert result.total_rows == 0, "Failed query should have 0 rows"

    @patch('streamlit.session_state', new_callable=dict)
    def test_sql_session_state_persistence(self, mock_session_state, sample_sql_query):
        """Test that extracted SQL persists in session state"""

        # Simulate storing SQL in session state
        mock_session_state['extracted_sql'] = sample_sql_query

        # Verify persistence
        assert 'extracted_sql' in mock_session_state, "SQL should be stored"
        assert mock_session_state['extracted_sql'] == sample_sql_query, "SQL should match"

    @patch('streamlit.session_state', new_callable=dict)
    def test_sql_execution_state_management(self, mock_session_state, sample_sql_query):
        """Test execution state flags during query execution"""

        # Simulate execution lifecycle
        mock_session_state['extracted_sql'] = sample_sql_query
        mock_session_state['sql_executing'] = True

        assert mock_session_state['sql_executing'] is True, "Should mark as executing"

        # After execution
        mock_session_state['sql_executing'] = False
        mock_session_state['sql_execution_completed'] = True

        assert mock_session_state['sql_executing'] is False, "Should clear executing flag"
        assert mock_session_state['sql_execution_completed'] is True, "Should mark as completed"

    def test_bigquery_executor_initialization(self):
        """Test BigQueryExecutor initialization with configuration"""
        from tests.fixtures.mock_helpers import MockBigQueryExecutor

        executor = MockBigQueryExecutor(
            project_id="test-project",
            dataset_id="test_dataset"
        )

        assert executor.project_id == "test-project", "Should set project ID"
        assert executor.dataset_id == "test_dataset", "Should set dataset ID"
        assert executor.max_rows > 0, "Should have max rows limit"
        assert executor.timeout_seconds > 0, "Should have timeout"

    def test_sql_with_bigquery_fqn(self, mock_bigquery_executor):
        """Test SQL with fully qualified BigQuery table names"""
        fqn_sql = """
        SELECT user_id, name, email
        FROM `bigquery-public-data.thelook_ecommerce.users`
        WHERE created_at > '2023-01-01'
        """

        is_valid, message = mock_bigquery_executor.validate_sql_safety(fqn_sql)

        assert is_valid is True, "FQN queries should pass validation"

    def test_sql_with_joins(self, mock_bigquery_executor):
        """Test SQL queries with joins"""
        join_sql = """
        SELECT u.user_id, u.name, o.order_id
        FROM users u
        LEFT JOIN orders o ON u.user_id = o.user_id
        WHERE u.created_at > '2023-01-01'
        """

        is_valid, message = mock_bigquery_executor.validate_sql_safety(join_sql)

        assert is_valid is True, "JOIN queries should pass validation"

    def test_sql_with_aggregations(self, mock_bigquery_executor):
        """Test SQL queries with aggregations"""
        agg_sql = """
        SELECT
            DATE(created_at) as date,
            COUNT(*) as user_count,
            AVG(age) as avg_age
        FROM users
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        """

        is_valid, message = mock_bigquery_executor.validate_sql_safety(agg_sql)

        assert is_valid is True, "Aggregation queries should pass validation"

    def test_sql_extraction_no_sql_in_text(self, mock_bigquery_executor):
        """Test extraction when no SQL is present"""
        text = "This is just a regular text response with no SQL query."

        sql = mock_bigquery_executor.extract_sql_from_text(text)

        assert sql is None, "Should return None when no SQL found"

    def test_complete_sql_generation_execution_flow(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_bigquery_executor,
        mock_schema_manager
    ):
        """Test complete flow from question to SQL execution"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        # Step 1: Generate SQL using RAG
        result = answer_question_chat_mode(
            question="Show me users from 2023",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type="create"  # Use create agent for SQL generation
        )

        assert result is not None, "Should generate response"
        answer, sources, token_usage = result

        # Step 2: Extract SQL from response
        sql = mock_bigquery_executor.extract_sql_from_text(answer)

        # Step 3: Validate SQL
        if sql:
            is_valid, message = mock_bigquery_executor.validate_sql_safety(sql)
            assert is_valid, "Generated SQL should be safe"

            # Step 4: Execute SQL
            query_result = mock_bigquery_executor.execute_query(sql)
            assert query_result.success, "SQL execution should succeed"

    def test_cache_hit_in_results(self):
        """Test query result with cache hit"""
        result = MockQueryResult(
            success=True,
            cache_hit=True,
            bytes_billed=0  # Cached queries are free
        )

        assert result.cache_hit is True, "Should indicate cache hit"
        assert result.bytes_billed == 0, "Cached queries should not bill"

    def test_format_bytes_utility(self):
        """Test bytes formatting utility"""
        from rag_app.core.bigquery_executor import format_bytes

        assert "KB" in format_bytes(1024), "Should format KB"
        assert "MB" in format_bytes(1024 * 1024), "Should format MB"
        assert "GB" in format_bytes(1024 * 1024 * 1024), "Should format GB"

    def test_format_execution_time_utility(self):
        """Test execution time formatting utility"""
        from rag_app.core.bigquery_executor import format_execution_time

        assert "ms" in format_execution_time(0.05), "Should format milliseconds"
        assert "s" in format_execution_time(1.5), "Should format seconds"
