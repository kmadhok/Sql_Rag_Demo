#!/usr/bin/env python3
"""
API Tests for Saved Query Endpoints

Tests the following endpoints with REAL Firestore:
- POST /saved_queries - Save a query result
- GET /saved_queries - List all saved queries
- GET /saved_queries/{id} - Get specific saved query

These tests validate the HTTP layer with real Firestore storage.
NO MOCKS - validates actual data persistence.
"""

import pytest
import re
from datetime import datetime


@pytest.mark.api
@pytest.mark.firestore
class TestSavedQueryEndpoints:
    """Test suite for saved query CRUD operations"""

    def test_create_saved_query_with_data(
        self,
        api_client,
        api_test_logger,
        cleanup_test_saved_queries,
        sample_saved_query_data
    ):
        """Test creating a saved query with data"""
        api_test_logger.info("Testing POST /saved_queries with data")

        response = api_client.post("/saved_queries", json=sample_saved_query_data)

        # Validate HTTP response
        assert response.status_code in [200, 201], \
            f"Expected 200/201, got {response.status_code}: {response.text}"

        data = response.json()
        api_test_logger.info(f"Created saved query: {data.get('id')}")

        # Track for cleanup
        query_id = data.get("id")
        cleanup_test_saved_queries.add(query_id)

        # Validate response structure
        assert "id" in data, "Response should contain id"
        assert "question" in data, "Response should contain question"
        assert "sql" in data, "Response should contain sql"
        assert "created_at" in data, "Response should contain created_at"
        assert "row_count" in data, "Response should contain row_count"
        assert "data_preview" in data, "Response should contain data_preview"

        # Validate ID is UUID format
        assert query_id, "ID should not be empty"
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_pattern, query_id), f"ID should be UUID format: {query_id}"

        # Validate question matches
        assert data["question"] == sample_saved_query_data["question"]

        # Validate SQL matches
        assert data["sql"] == sample_saved_query_data["sql"]

        # Validate created_at is ISO timestamp
        created_at = data.get("created_at")
        assert created_at, "created_at should not be empty"
        # Should be parseable as ISO datetime
        try:
            datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"created_at should be ISO format: {created_at}")

        # Validate row_count
        row_count = data.get("row_count")
        assert isinstance(row_count, int), "row_count should be integer"
        assert row_count == len(sample_saved_query_data["data"])

        # Validate data_preview
        data_preview = data.get("data_preview", [])
        assert isinstance(data_preview, list), "data_preview should be list"
        assert len(data_preview) > 0, "data_preview should not be empty"

    def test_create_saved_query_without_data(
        self,
        api_client,
        cleanup_test_saved_queries
    ):
        """Test creating a saved query without data"""
        payload = {
            "question": "Test query without data",
            "sql": "SELECT * FROM products LIMIT 10",
            "data": None  # No data
        }

        response = api_client.post("/saved_queries", json=payload)
        assert response.status_code in [200, 201]

        data = response.json()
        query_id = data.get("id")
        cleanup_test_saved_queries.add(query_id)

        # Should accept query without data
        assert data.get("row_count") == 0 or data.get("row_count") is None
        assert data.get("data_preview") == [] or data.get("data_preview") is None

    def test_list_saved_queries_returns_summaries(
        self,
        api_client,
        api_test_logger,
        create_test_saved_query
    ):
        """Test listing all saved queries"""
        api_test_logger.info("Testing GET /saved_queries")

        # Create a test query first
        query_id = create_test_saved_query()
        api_test_logger.info(f"Created test query: {query_id}")

        # List all queries
        response = api_client.get("/saved_queries")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list), "Response should be a list"

        api_test_logger.info(f"Found {len(data)} saved queries")

        # Find our test query
        test_query = next((q for q in data if q.get("id") == query_id), None)
        assert test_query is not None, f"Test query {query_id} should be in list"

        # Validate summary structure (should NOT include data_preview)
        assert "id" in test_query
        assert "question" in test_query
        assert "created_at" in test_query
        assert "row_count" in test_query

        # Summaries should NOT include sql or data_preview
        assert "sql" not in test_query, "Summary should not include sql"
        assert "data_preview" not in test_query, "Summary should not include data_preview"

    def test_list_saved_queries_when_empty(self, api_client):
        """Test listing saved queries when there are none (or few)"""
        response = api_client.get("/saved_queries")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list), "Should return empty list if no queries"

    def test_get_saved_query_by_id_returns_full_detail(
        self,
        api_client,
        api_test_logger,
        create_test_saved_query,
        sample_saved_query_data
    ):
        """Test getting a specific saved query by ID"""
        # Create a test query
        query_id = create_test_saved_query()
        api_test_logger.info(f"Testing GET /saved_queries/{query_id}")

        # Get the specific query
        response = api_client.get(f"/saved_queries/{query_id}")
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"Retrieved query: {data.keys()}")

        # Validate full detail structure (should include everything)
        assert "id" in data
        assert "question" in data
        assert "sql" in data
        assert "created_at" in data
        assert "row_count" in data
        assert "data_preview" in data

        # Validate ID matches
        assert data["id"] == query_id

        # Validate data_preview is present (since we created with data)
        data_preview = data.get("data_preview", [])
        assert len(data_preview) > 0, "Should include data_preview for detail view"

    def test_get_saved_query_with_invalid_id_returns_404(
        self,
        api_client,
        api_test_logger
    ):
        """Test that invalid query ID returns 404"""
        invalid_id = "nonexistent-query-id-12345"
        api_test_logger.info(f"Testing GET /saved_queries/{invalid_id} (should 404)")

        response = api_client.get(f"/saved_queries/{invalid_id}")

        # Should return 404 for nonexistent query
        assert response.status_code == 404, \
            f"Expected 404 for invalid ID, got {response.status_code}"

    def test_save_large_data_preview_is_limited(
        self,
        api_client,
        cleanup_test_saved_queries
    ):
        """Test that data preview is limited (e.g., first 10 rows)"""
        # Create query with many rows
        large_data = [{"id": i, "value": f"row_{i}"} for i in range(100)]

        payload = {
            "question": "Test query with large result set",
            "sql": "SELECT * FROM large_table",
            "data": large_data
        }

        response = api_client.post("/saved_queries", json=payload)
        assert response.status_code in [200, 201]

        data = response.json()
        query_id = data.get("id")
        cleanup_test_saved_queries.add(query_id)

        # Data preview should be limited
        data_preview = data.get("data_preview", [])
        assert len(data_preview) <= 10, \
            f"Data preview should be limited to 10 rows, got {len(data_preview)}"

        # But row_count should reflect total
        assert data.get("row_count") == 100, "Row count should reflect total rows"

    def test_saved_queries_persist_across_requests(
        self,
        api_client,
        create_test_saved_query
    ):
        """Test that saved queries persist across multiple requests"""
        # Create a query
        query_id = create_test_saved_query()

        # Retrieve it multiple times
        response1 = api_client.get(f"/saved_queries/{query_id}")
        response2 = api_client.get(f"/saved_queries/{query_id}")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Should return same data
        data1 = response1.json()
        data2 = response2.json()

        assert data1["id"] == data2["id"]
        assert data1["question"] == data2["question"]
        assert data1["sql"] == data2["sql"]

    def test_multiple_saved_queries_are_independent(
        self,
        api_client,
        cleanup_test_saved_queries,
        sample_saved_query_data
    ):
        """Test that multiple saved queries are stored independently"""
        # Create two different queries
        query1_data = sample_saved_query_data.copy()
        query1_data["question"] = "First test query"

        query2_data = sample_saved_query_data.copy()
        query2_data["question"] = "Second test query"
        query2_data["sql"] = "SELECT * FROM users LIMIT 5"

        response1 = api_client.post("/saved_queries", json=query1_data)
        response2 = api_client.post("/saved_queries", json=query2_data)

        assert response1.status_code in [200, 201]
        assert response2.status_code in [200, 201]

        query1_id = response1.json()["id"]
        query2_id = response2.json()["id"]

        cleanup_test_saved_queries.add(query1_id)
        cleanup_test_saved_queries.add(query2_id)

        # IDs should be different
        assert query1_id != query2_id, "Each query should have unique ID"

        # Retrieve both and validate they're different
        get1 = api_client.get(f"/saved_queries/{query1_id}").json()
        get2 = api_client.get(f"/saved_queries/{query2_id}").json()

        assert get1["question"] == "First test query"
        assert get2["question"] == "Second test query"
        assert get1["sql"] != get2["sql"]
