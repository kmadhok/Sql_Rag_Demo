#!/usr/bin/env python3
"""
API Tests for Query Endpoints

Tests the following endpoints with REAL services:
- POST /query/search - Main RAG query with SQL generation
- POST /query/quick - Quick concise answers

These tests validate the HTTP layer with real RAG pipeline.
NO MOCKS - validates actual Gemini API, FAISS retrieval, and BigQuery.
"""

import pytest


@pytest.mark.api
@pytest.mark.slow
class TestQuerySearchEndpoint:
    """Test suite for POST /query/search endpoint"""

    def test_simple_product_query_returns_sql(self, api_client, api_test_logger):
        """Test simple product query generates valid SQL"""
        api_test_logger.info("Testing POST /query/search - simple product query")

        payload = {
            "question": "Show me the 10 most expensive products",
            "k": 10,
            "gemini_mode": False
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"Query response keys: {data.keys()}")

        # Validate response structure
        assert "sql" in data, "Response should contain sql"
        assert "sources" in data, "Response should contain sources"
        assert "natural_language_response" in data, "Response should contain NL response"

        # Validate SQL content
        sql = data.get("sql", "")
        assert sql, "SQL should not be empty"
        assert "SELECT" in sql.upper(), "SQL should contain SELECT"
        assert "product" in sql.lower(), "SQL should reference products table"

        # Validate sources
        sources = data.get("sources", [])
        assert len(sources) > 0, "Should have at least one source"
        assert len(sources) <= 10, f"Should have at most k={10} sources"

    def test_user_query_returns_sql(self, api_client):
        """Test user-related query"""
        payload = {
            "question": "How many users registered last month?",
            "k": 5
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        sql = data.get("sql", "")

        assert "SELECT" in sql.upper()
        # Should reference users or related table
        assert any(keyword in sql.lower() for keyword in ["user", "customer"])

    def test_order_query_returns_sql(self, api_client):
        """Test order-related query"""
        payload = {
            "question": "What are the total sales by month?",
            "k": 5
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        sql = data.get("sql", "")

        assert "SELECT" in sql.upper()
        # Should have aggregation
        assert any(keyword in sql.upper() for keyword in ["SUM", "COUNT", "AVG", "GROUP BY"])

    def test_query_with_custom_k_parameter(self, api_client, api_test_logger):
        """Test that k parameter controls number of retrieved sources"""
        k_value = 3

        payload = {
            "question": "Show me recent orders",
            "k": k_value
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        sources = data.get("sources", [])

        api_test_logger.info(f"Retrieved {len(sources)} sources with k={k_value}")

        # Should retrieve at most k sources
        assert len(sources) <= k_value, \
            f"Should retrieve at most {k_value} sources, got {len(sources)}"

    def test_query_with_gemini_mode_enabled(self, api_client, api_test_logger):
        """Test query with Gemini optimization mode"""
        payload = {
            "question": "List all product categories",
            "k": 5,
            "gemini_mode": True
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info("Gemini mode query successful")

        # Validate standard response structure
        assert "sql" in data
        assert "sources" in data

    def test_query_without_gemini_mode(self, api_client):
        """Test query with Gemini mode disabled"""
        payload = {
            "question": "Show product details",
            "k": 5,
            "gemini_mode": False
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        # Should still work
        data = response.json()
        assert "sql" in data

    def test_complex_join_query(self, api_client, api_test_logger):
        """Test query that requires table joins"""
        payload = {
            "question": "Show me users who ordered products in the Electronics category",
            "k": 10
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        sql = data.get("sql", "")

        api_test_logger.info(f"Join query SQL: {sql[:200]}...")

        # Should have JOIN if query requires it
        # (This is a soft check - depends on schema structure)
        assert "SELECT" in sql.upper()

    def test_aggregation_query(self, api_client):
        """Test query with aggregation functions"""
        payload = {
            "question": "What is the average order value by user?",
            "k": 5
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        sql = data.get("sql", "")

        # Should have aggregation function
        assert any(func in sql.upper() for func in ["AVG", "SUM", "COUNT", "MIN", "MAX"])

    def test_date_range_query(self, api_client):
        """Test query with date filtering"""
        payload = {
            "question": "Show orders from the last 30 days",
            "k": 5
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        sql = data.get("sql", "")

        # Should have date filtering
        assert any(keyword in sql.upper() for keyword in ["DATE", "TIMESTAMP", "WHERE"])

    def test_sorting_query(self, api_client):
        """Test query with sorting requirement"""
        payload = {
            "question": "List top selling products ordered by revenue",
            "k": 5
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        sql = data.get("sql", "")

        # Should have ORDER BY
        assert "ORDER BY" in sql.upper()

    def test_limit_query(self, api_client):
        """Test query with LIMIT clause"""
        payload = {
            "question": "Show me 5 sample users",
            "k": 5
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        sql = data.get("sql", "")

        # Should have LIMIT
        assert "LIMIT" in sql.upper()

    def test_missing_question_fails_validation(self, api_client):
        """Test that missing question field fails validation"""
        payload = {
            # Missing "question" field
            "k": 5
        }

        response = api_client.post("/query/search", json=payload)

        # Should return 422 validation error
        assert response.status_code == 422, \
            f"Expected 422 for missing question, got {response.status_code}"

    def test_empty_question_fails_validation(self, api_client):
        """Test that empty question fails validation"""
        payload = {
            "question": "",
            "k": 5
        }

        response = api_client.post("/query/search", json=payload)

        # Should return 422 validation error
        assert response.status_code == 422, \
            f"Expected 422 for empty question, got {response.status_code}"

    def test_invalid_k_parameter_fails_validation(self, api_client):
        """Test that invalid k parameter fails validation"""
        payload = {
            "question": "Show products",
            "k": -5  # Invalid negative k
        }

        response = api_client.post("/query/search", json=payload)

        # Should return 422 validation error
        assert response.status_code == 422

    def test_response_includes_metadata(self, api_client, api_test_logger):
        """Test that response includes metadata about sources"""
        payload = {
            "question": "Show all products",
            "k": 3
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        sources = data.get("sources", [])

        # Validate source structure
        if len(sources) > 0:
            first_source = sources[0]
            api_test_logger.info(f"Sample source: {first_source.keys()}")

            # Sources should have metadata
            assert isinstance(first_source, dict)

    def test_natural_language_response_exists(self, api_client):
        """Test that NL response is generated"""
        payload = {
            "question": "How many products are there?",
            "k": 5
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        nl_response = data.get("natural_language_response", "")

        assert nl_response, "Natural language response should not be empty"
        assert len(nl_response) > 10, "NL response should be meaningful"

    def test_query_with_very_specific_question(self, api_client):
        """Test highly specific query"""
        payload = {
            "question": "What is the total revenue from products in the Electronics category sold in California in 2023?",
            "k": 10
        }

        response = api_client.post("/query/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        sql = data.get("sql", "")

        # Should generate SQL (quality validation is for integration tests)
        assert "SELECT" in sql.upper()

    def test_query_with_ambiguous_question(self, api_client):
        """Test ambiguous query that needs interpretation"""
        payload = {
            "question": "Show me the data",
            "k": 5
        }

        response = api_client.post("/query/search", json=payload)

        # Should still return 200 (may generate generic query)
        assert response.status_code == 200

    def test_query_caching_behavior(self, api_client, api_test_logger):
        """Test that repeated queries work consistently"""
        payload = {
            "question": "List all product categories",
            "k": 5
        }

        # First request
        response1 = api_client.post("/query/search", json=payload)
        assert response1.status_code == 200
        data1 = response1.json()

        # Second request (same question)
        response2 = api_client.post("/query/search", json=payload)
        assert response2.status_code == 200
        data2 = response2.json()

        # Both should succeed
        assert "sql" in data1
        assert "sql" in data2

        api_test_logger.info("Repeated query executed successfully")

    def test_special_characters_in_question(self, api_client):
        """Test question with special characters"""
        payload = {
            "question": "Show products with price > $100 & rating >= 4.5",
            "k": 5
        }

        response = api_client.post("/query/search", json=payload)

        # Should handle special characters
        assert response.status_code == 200


@pytest.mark.api
@pytest.mark.slow
class TestQueryQuickEndpoint:
    """Test suite for POST /query/quick endpoint"""

    def test_quick_answer_for_simple_question(self, api_client, api_test_logger):
        """Test quick answer for simple factual question"""
        api_test_logger.info("Testing POST /query/quick")

        payload = {
            "question": "What data is available?"
        }

        response = api_client.post("/query/quick", json=payload)
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"Quick answer response: {data}")

        # Validate response structure
        assert "answer" in data, "Response should contain answer"
        assert "sources_used" in data, "Response should contain sources_used count"

        # Validate answer content
        answer = data.get("answer", "")
        assert answer, "Answer should not be empty"
        assert len(answer) > 10, "Answer should be meaningful"

    def test_quick_answer_conciseness(self, api_client):
        """Test that quick answers are concise"""
        payload = {
            "question": "How many tables are in the database?"
        }

        response = api_client.post("/query/quick", json=payload)
        assert response.status_code == 200

        data = response.json()
        answer = data.get("answer", "")

        # Quick answers should be brief (< 500 chars typically)
        assert len(answer) < 1000, "Quick answer should be concise"

    def test_quick_answer_with_context(self, api_client):
        """Test quick answer uses retrieved context"""
        payload = {
            "question": "What types of queries can I ask about products?"
        }

        response = api_client.post("/query/quick", json=payload)
        assert response.status_code == 200

        data = response.json()

        # Should have used sources
        sources_used = data.get("sources_used", 0)
        assert sources_used > 0, "Quick answer should use retrieved sources"

    def test_quick_answer_missing_question_fails(self, api_client):
        """Test that missing question fails validation"""
        payload = {}

        response = api_client.post("/query/quick", json=payload)

        # Should return 422 validation error
        assert response.status_code == 422

    def test_quick_answer_empty_question_fails(self, api_client):
        """Test that empty question fails validation"""
        payload = {
            "question": ""
        }

        response = api_client.post("/query/quick", json=payload)

        # Should return 422 validation error
        assert response.status_code == 422
