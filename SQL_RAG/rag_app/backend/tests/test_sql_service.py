"""
Tests for SQL Service

This test suite verifies:
1. SQL validation and security
2. Query execution functionality 
3. Result formatting
4. Error handling
5. Edge cases
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import our service and models
from services.sql_service import SQLService
from api.sql import ExecuteSQLRequest, ExecuteSQLResponse

class TestSQLService:
    """Test suite for SQL Service functionality"""
    
    @pytest.fixture
    def sql_service(self):
        """Create a fresh SQLService instance for each test"""
        return SQLService()
    
    # ==================== SECURITY TESTS ====================
    
    @pytest.mark.asyncio
    async def test_validate_safe_select_query(self, sql_service):
        """Test that safe SELECT queries pass validation"""
        safe_queries = [
            "SELECT * FROM users LIMIT 10;",
            "SELECT name, email FROM users WHERE id > 100;",
            "SELECT COUNT(*) FROM orders;",
            "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id;",
            "WITH user_stats AS (SELECT id, name FROM users) SELECT * FROM user_stats;"
        ]
        
        for query in safe_queries:
            result = await sql_service._validate_sql(query)
            assert result['valid'] == True, f"Should be valid: {query}"
            assert result['error'] is None
    
    @pytest.mark.asyncio
    async def test_reject_dangerous_queries(self, sql_service):
        """Test that dangerous SQL queries are rejected"""
        dangerous_queries = [
            "DROP TABLE users;",
            "DELETE FROM users WHERE id = 1;",
            "UPDATE users SET role = 'admin';",
            "INSERT INTO users VALUES (1, 'test');",
            "CREATE TABLE test (id INT);",
            "ALTER TABLE users ADD COLUMN test INT;",
            "TRUNCATE TABLE users;",
            "EXEC xp_cmdshell 'dir';",
            "SELECT * FROM users; DROP TABLE users;"  # SQL injection attempt
        ]
        
        for query in dangerous_queries:
            result = await sql_service._validate_sql(query)
            assert result['valid'] == False, f"Should be invalid: {query}"
            assert result['error'] is not None
    
    @pytest.mark.asyncio
    async def test_reject_non_select_queries(self, sql_service):
        """Test that non-SELECT queries are rejected"""
        invalid_queries = [
            "SHOW TABLES;",
            "DESCRIBE users;",
            "EXPLAIN SELECT * FROM users;",
            "BEGIN TRANSACTION;",
            "COMMIT;",
            "ROLLBACK;"
        ]
        
        for query in invalid_queries:
            result = await sql_service._validate_sql(query)
            assert result['valid'] == False, f"Should be invalid: {query}"
            assert "not allowed" in result['error']
    
    @pytest.mark.asyncio
    async def test_require_semicolon(self, sql_service):
        """Test that SQL queries must end with semicolon"""
        invalid_queries = [
            "SELECT * FROM users",
            "SELECT * FROM users  ",  # trailing spaces but no semicolon
            "SELECT * FROM users\n\n"  # newlines but no semicolon
        ]
        
        for query in invalid_queries:
            result = await sql_service._validate_sql(query)
            assert result['valid'] == False
            assert "semicolon" in result['error']
    
    # ==================== EXECUTION TESTS ====================
    
    @pytest.mark.asyncio
    @patch('services.sql_service.bigquery.Client')
    async def test_execute_query_success(self, mock_bigquery_client, sql_service):
        """Test successful query execution"""
        # Mock BigQuery response
        mock_query_job = Mock()
        mock_query_job.result.return_value = [
            (1, "John", "john@example.com"),
            (2, "Jane", "jane@example.com")
        ]
        mock_query_job.total_bytes_processed = 1000
        mock_query_job.num_dml_affected_rows = 2
        
        # Mock schema
        mock_schema = Mock()
        mock_field1 = Mock()
        mock_field1.name = "id"
        mock_field1.field_type = "INTEGER"
        mock_field2 = Mock()
        mock_field2.name = "name"
        mock_field2.field_type = "STRING"
        mock_field3 = Mock()
        mock_field3.name = "email"
        mock_field3.field_type = "STRING"
        
        mock_query_job.result.return_value.schema = [mock_field1, mock_field2, mock_field3]
        mock_client_instance = Mock()
        mock_client_instance.query.return_value = mock_query_job
        mock_bigquery_client.return_value = mock_client_instance
        
        sql_service.client = mock_client_instance
        
        # Execute query
        result = await sql_service.execute_query("SELECT * FROM users;")
        
        # Verify result
        assert result['success'] == True
        assert result['total_rows'] == 2
        assert result['data'] == [
            {"id": 1, "name": "John", "email": "john@example.com"},
            {"id": 2, "name": "Jane", "email": "jane@example.com"}
        ]
        assert result['column_types'] == {
            "id": "INTEGER",
            "name": "STRING", 
            "email": "STRING"
        }
        assert result['bytes_processed'] == 1000
    
    @pytest.mark.asyncio
    async def test_execute_query_dry_run(self, sql_service):
        """Test dry run functionality"""
        # Mock BigQuery response for dry run
        mock_query_job = Mock()
        mock_query_job.total_bytes_processed = 1000
        mock_query_job.num_dml_affected_rows = 0  # No rows affected in dry run
        
        mock_client_instance = Mock()
        mock_client_instance.query.return_value = mock_query_job
        sql_service.client = mock_client_instance
        
        # Execute dry run
        result = await sql_service.execute_query("SELECT * FROM users;", dry_run=True)
        
        # Verify dry run result
        assert result['success'] == True
        assert result['dry_run'] == True
        assert result['total_rows'] == 0  # Should be 0 for SELECT dry run
        assert result['data'] is None
        assert result['column_types'] is None
        assert result['message'] == 'Query validated successfully'
        assert result['cost'] == 0.0  # No cost for dry run
    
    @pytest.mark.asyncio
    @patch('services.sql_service.bigquery.Client')
    async def test_execute_query_with_validation_error(self, mock_bigquery_client, sql_service):
        """Test execution when validation fails"""
        sql_service.client = Mock()  # We don't need BigQuery for this test
        
        # Try dangerous query
        result = await sql_service.execute_query("DROP TABLE users;")
        
        # Should fail validation
        assert result['success'] == False
        assert 'danger' in result['error_message']
        assert result['total_rows'] == 0
        assert result['data'] is None
    
    @pytest.mark.asyncio
    @patch('services.sql_service.bigquery.Client')
    async def test_execute_query_bigquery_error(self, mock_bigquery_client, sql_service):
        """Test handling of BigQuery errors"""
        from google.api_core.exceptions import GoogleAPICallError
        
        # Mock BigQuery throwing an error
        mock_client_instance = Mock()
        mock_client_instance.query.side_effect = GoogleAPICallError("Dataset not found")
        mock_bigquery_client.return_value = mock_client_instance
        sql_service.client = mock_client_instance
        
        # Execute query
        result = await sql_service.execute_query("SELECT * FROM invalid_table;")
        
        # Should handle error gracefully
        assert result['success'] == False
        assert 'BigQuery error' in result['error_message']
        assert result['total_rows'] == 0
        assert result['data'] is None
    
    @pytest.mark.asyncio
    async def test_cost_calculation(self, sql_service):
        """Test cost calculation for queries"""
        # Mock BigQuery response
        mock_query_job = Mock()
        mock_query_job.total_bytes_processed = 5368709120  # 5 GB
        mock_query_job.num_dml_affected_rows = 100
        mock_query_job.result.return_value = []  # Empty result
        mock_query_job.result.return_value.schema = []
        
        mock_client_instance = Mock()
        mock_client_instance.query.return_value = mock_query_job
        sql_service.client = mock_client_instance
        
        # Execute query
        result = await sql_service.execute_query("SELECT * FROM large_table;")
        
        # Expected cost: 5GB * $6/TB = $30
        expected_cost = 5368709120 / 1024 / 1024 / 1024  # Convert bytes to GB
        expected_cost = expected_cost * 6.0  # $6 per GB
        
        assert result['success'] == True
        assert result['cost'] == expected_cost
        assert result['bytes_processed'] == 5368709120
    
    # ==================== EDGE CASES ====================
    
    @pytest.mark.asyncio
    async def test_empty_result_set(self, sql_service):
        """Test handling of queries that return no results"""
        # Mock empty result
        mock_query_job = Mock()
        mock_query_job.result.return_value = []  # Empty list
        mock_query_job.result.return_value.schema = []  # No columns
        mock_query_job.total_bytes_processed = 100
        mock_query_job.num_dml_affected_rows = 0
        
        mock_client_instance = Mock()
        mock_client_instance.query.return_value = mock_query_job
        sql_service.client = mock_client_instance
        
        result = await sql_service.execute_query("SELECT * FROM empty_table;")
        
        assert result['success'] == True
        assert result['total_rows'] == 0
        assert result['data'] == []
        assert result['column_types'] == {}
    
    @pytest.mark.asyncio
    async def test_large_result_set(self, sql_service):
        """Test handling of queries that return many results"""
        # Mock large result set
        mock_rows = [(i, f"user_{i}") for i in range(1000)]  # 1000 rows
        
        mock_field1 = Mock()
        mock_field1.name = "id"
        mock_field1.field_type = "INTEGER"
        mock_field2 = Mock()
        mock_field2.name = "name"
        mock_field2.field_type = "STRING"
        
        mock_query_job = Mock()
        mock_query_job.result.return_value = mock_rows
        mock_query_job.result.return_value.schema = [mock_field1, mock_field2]
        mock_query_job.total_bytes_processed = 50000000  # 50MB
        mock_query_job.num_dml_affected_rows = 1000
        
        mock_client_instance = Mock()
        mock_client_instance.query.return_value = mock_query_job
        sql_service.client = mock_client_instance
        
        result = await sql_service.execute_query("SELECT * FROM large_table;")
        
        assert result['success'] == True
        assert result['total_rows'] == 1000
        assert len(result['data']) == 1000
        assert result['data'][0] == {"id": 0, "name": "user_0"}
        assert result['data'][999] == {"id": 999, "name": "user_999"}
    
    @pytest.mark.asyncio
    async def test_null_values_in_results(self, sql_service):
        """Test handling of NULL values in query results"""
        # Mock result with NULL values
        mock_rows = [(1, "John", None, "2024-01-15"), (2, None, "jane@test.com", None)]
        
        mock_fields = []
        for name, field_type in [("id", "INTEGER"), ("name", "STRING"), ("email", "STRING"), ("date", "DATE")]:
            mock_field = Mock()
            mock_field.name = name
            mock_field.field_type = field_type
            mock_fields.append(mock_field)
        
        mock_query_job = Mock()
        mock_query_job.result.return_value = mock_rows
        mock_query_job.result.return_value.schema = mock_fields
        mock_query_job.total_bytes_processed = 1000
        mock_query_job.num_dml_affected_rows = 2
        
        mock_client_instance = Mock()
        mock_client_instance.query.return_value = mock_query_job
        sql_service.client = mock_client_instance
        
        result = await sql_service.execute_query("SELECT * FROM users_with_nulls;")
        
        assert result['success'] == True
        assert result['total_rows'] == 2
        assert result['data'][0] == {"id": 1, "name": "John", "email": None, "date": "2024-01-15"}
        assert result['data'][1] == {"id": 2, "name": None, "email": "jane@test.com", "date": None}


class TestSQLAPI:
    """Test suite for SQL API endpoints"""
    
    @pytest.mark.asyncio
    async def test_sql_execute_endpoint_success(self):
        """Test the SQL execute API endpoint"""
        # Import here to avoid circular imports
        from api.sql import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router, prefix="/api/sql")
        
        client = TestClient(app)
        
        # Test successful execution
        response = client.post("/api/sql/execute", json={
            "sql": "SELECT COUNT(*) as user_count FROM users",
            "dry_run": False
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert data['row_count'] == 1
        assert data['columns'] == ["user_count"]
        assert isinstance(data['timestamp'], str)
    
    def test_sql_validate_endpoint(self):
        """Test the SQL validation API endpoint"""
        from api.sql import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router, prefix="/api/sql")
        
        client = TestClient(app)
        
        # Test safe SQL
        response = client.get("/api/sql/validate?sql=SELECT * FROM users LIMIT 10;")
        assert response.status_code == 200
        data = response.json()
        assert data['valid'] == True
        assert "safe" in data['message']
        
        # Test dangerous SQL
        response = client.get("/api/sql/validate?sql=DROP TABLE users;")
        assert response.status_code == 200
        data = response.json()
        assert data['valid'] == False
        assert "dangerous" in data['message']
    
    def test_sql_history_endpoint(self):
        """Test the SQL history API endpoint"""
        from api.sql import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router, prefix="/api/sql")
        
        client = TestClient(app)
        
        response = client.get("/api/sql/history")
        assert response.status_code == 200
        data = response.json()
        assert 'history' in data
        assert 'count' in data
        assert len(data['history']) <= 50
        
        # Check structure of history items
        if data['history']:
            history_item = data['history'][0]
            assert 'id' in history_item
            assert 'sql' in history_item
            assert 'execution_time' in history_item
            assert 'row_count' in history_item
            assert 'timestamp' in history_item
            assert 'success' in history_item

if __name__ == "__main__":
    pytest.main([__file__, "-v"])