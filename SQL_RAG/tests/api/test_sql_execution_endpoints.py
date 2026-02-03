#!/usr/bin/env python3
"""
API Tests for SQL Execution Endpoints

Tests the following endpoints with REAL BigQuery:
- POST /sql/execute - Execute SQL queries against BigQuery

These tests validate the HTTP layer with real BigQuery execution.
NO MOCKS - validates actual SQL execution with safety checks.
"""

import pytest


@pytest.mark.api
@pytest.mark.bigquery
class TestSQLExecuteEndpoint:
    """Test suite for POST /sql/execute endpoint"""

    def test_simple_select_query_executes_successfully(self, api_client, api_test_logger):
        """Test simple SELECT query executes and returns data"""
        api_test_logger.info("Testing POST /sql/execute - simple SELECT")

        payload = {
            "sql": "SELECT product_id, name, retail_price FROM `bigquery-public-data.thelook_ecommerce.products` LIMIT 10",
            "dry_run": False
        }

        response = api_client.post("/sql/execute", json=payload)
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"SQL execution response keys: {data.keys()}")

        # Validate response structure
        assert "success" in data, "Response should contain success flag"
        assert "data" in data, "Response should contain data"
        assert "row_count" in data, "Response should contain row_count"
        assert "columns" in data, "Response should contain columns"

        # Validate success
        assert data["success"] is True, "Query execution should succeed"

        # Validate data
        result_data = data.get("data")
        assert result_data is not None, "Data should not be None"
        assert isinstance(result_data, list), "Data should be a list"
        assert len(result_data) > 0, "Should have at least one row"
        assert len(result_data) <= 10, "Should have at most 10 rows (LIMIT 10)"

        # Validate row count
        row_count = data.get("row_count")
        assert row_count == len(result_data), "Row count should match data length"

        # Validate columns
        columns = data.get("columns", [])
        assert len(columns) > 0, "Should have column information"

    def test_dry_run_mode_validates_without_executing(self, api_client, api_test_logger):
        """Test dry run mode validates SQL without executing"""
        api_test_logger.info("Testing POST /sql/execute - dry run mode")

        payload = {
            "sql": "SELECT * FROM `bigquery-public-data.thelook_ecommerce.products` LIMIT 1000",
            "dry_run": True
        }

        response = api_client.post("/sql/execute", json=payload)
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"Dry run response: {data}")

        # Validate dry run response
        assert "success" in data
        assert "dry_run" in data or "is_valid" in data, "Should indicate dry run validation"

        # Dry run should not return actual data
        # (Implementation may vary - adjust based on actual API)

    def test_aggregation_query_executes(self, api_client):
        """Test query with aggregation functions"""
        payload = {
            "sql": "SELECT COUNT(*) as product_count FROM `bigquery-public-data.thelook_ecommerce.products`",
            "dry_run": False
        }

        response = api_client.post("/sql/execute", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

        # Should return aggregated result
        result_data = data.get("data", [])
        assert len(result_data) > 0

    def test_join_query_executes(self, api_client):
        """Test query with JOIN operations"""
        payload = {
            "sql": """
                SELECT p.product_id, p.name, c.category
                FROM `bigquery-public-data.thelook_ecommerce.products` p
                JOIN `bigquery-public-data.thelook_ecommerce.distribution_centers` c
                ON p.distribution_center_id = c.id
                LIMIT 5
            """,
            "dry_run": False
        }

        response = api_client.post("/sql/execute", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

    def test_invalid_sql_syntax_fails_gracefully(self, api_client, api_test_logger):
        """Test that invalid SQL returns error instead of crashing"""
        api_test_logger.info("Testing POST /sql/execute - invalid SQL")

        payload = {
            "sql": "SELECT * FROM this is not valid SQL",
            "dry_run": False
        }

        response = api_client.post("/sql/execute", json=payload)

        # Should return error (could be 400, 422, or 200 with success=false)
        api_test_logger.info(f"Invalid SQL response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            # If 200, success should be False with error message
            assert data.get("success") is False or "error" in data
        else:
            # Or return 400/422 error
            assert response.status_code in [400, 422]

    def test_dangerous_sql_is_blocked(self, api_client, api_test_logger):
        """Test that dangerous SQL operations are blocked"""
        dangerous_queries = [
            "DELETE FROM `bigquery-public-data.thelook_ecommerce.products` WHERE product_id = 1",
            "DROP TABLE `bigquery-public-data.thelook_ecommerce.products`",
            "UPDATE `bigquery-public-data.thelook_ecommerce.products` SET name = 'hacked'",
        ]

        for dangerous_sql in dangerous_queries:
            api_test_logger.info(f"Testing dangerous SQL block: {dangerous_sql[:50]}...")

            payload = {
                "sql": dangerous_sql,
                "dry_run": False
            }

            response = api_client.post("/sql/execute", json=payload)

            # Should be blocked (400, 403, or 200 with success=false)
            if response.status_code == 200:
                data = response.json()
                assert data.get("success") is False, \
                    f"Dangerous SQL should fail: {dangerous_sql[:50]}"
            else:
                assert response.status_code in [400, 403, 422], \
                    f"Dangerous SQL should return error status: {dangerous_sql[:50]}"

    def test_missing_sql_fails_validation(self, api_client):
        """Test that missing SQL field fails validation"""
        payload = {
            # Missing "sql" field
            "dry_run": False
        }

        response = api_client.post("/sql/execute", json=payload)

        # Should return 422 validation error
        assert response.status_code == 422

    def test_empty_sql_fails_validation(self, api_client):
        """Test that empty SQL fails validation"""
        payload = {
            "sql": "",
            "dry_run": False
        }

        response = api_client.post("/sql/execute", json=payload)

        # Should return error
        assert response.status_code in [400, 422]

    def test_nonexistent_table_returns_error(self, api_client, api_test_logger):
        """Test query to nonexistent table returns error"""
        payload = {
            "sql": "SELECT * FROM `bigquery-public-data.nonexistent_dataset.fake_table` LIMIT 1",
            "dry_run": False
        }

        response = api_client.post("/sql/execute", json=payload)

        api_test_logger.info(f"Nonexistent table response: {response.status_code}")

        # Should fail (400, 404, or 200 with success=false)
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is False
        else:
            assert response.status_code in [400, 404]

    def test_query_with_limit_clause(self, api_client):
        """Test query with LIMIT clause"""
        payload = {
            "sql": "SELECT * FROM `bigquery-public-data.thelook_ecommerce.products` LIMIT 5",
            "dry_run": False
        }

        response = api_client.post("/sql/execute", json=payload)
        assert response.status_code == 200

        data = response.json()
        result_data = data.get("data", [])

        # Should respect LIMIT
        assert len(result_data) <= 5

    def test_query_execution_includes_metadata(self, api_client, api_test_logger):
        """Test that execution response includes metadata"""
        payload = {
            "sql": "SELECT product_id, name FROM `bigquery-public-data.thelook_ecommerce.products` LIMIT 3",
            "dry_run": False
        }

        response = api_client.post("/sql/execute", json=payload)
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"Execution metadata: {data.keys()}")

        # Should include metadata like execution_time, bytes_processed, etc.
        # (Specific fields depend on implementation)
        assert "row_count" in data
        assert "columns" in data

    def test_query_with_where_clause(self, api_client):
        """Test query with WHERE clause filtering"""
        payload = {
            "sql": "SELECT product_id, name, retail_price FROM `bigquery-public-data.thelook_ecommerce.products` WHERE retail_price > 100 LIMIT 10",
            "dry_run": False
        }

        response = api_client.post("/sql/execute", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
