#!/usr/bin/env python3
"""
API Tests for SQL Assistant Endpoints

Tests the following AI-powered endpoints with REAL Gemini API:
- POST /sql/explain - Generate SQL explanation
- POST /sql/complete - SQL autocomplete suggestions
- POST /sql/fix - Debug and fix broken SQL
- POST /sql/format - Format SQL query
- POST /sql/chat - Conversational SQL assistance

These tests validate the HTTP layer with real AI services.
NO MOCKS - validates actual AI-powered SQL assistance.
"""

import pytest
import time


@pytest.mark.api
@pytest.mark.slow
class TestSQLExplainEndpoint:
    """Test suite for POST /sql/explain endpoint"""

    def test_explain_simple_select_query(self, api_client, api_test_logger):
        """Test explaining a simple SELECT query"""
        api_test_logger.info("Testing /sql/explain with simple SELECT")

        payload = {
            "sql": "SELECT product_id, name, retail_price FROM products WHERE retail_price > 100 ORDER BY retail_price DESC LIMIT 10"
        }

        response = api_client.post("/sql/explain", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True, f"Explain should succeed: {data.get('error')}"

        # Validate response structure
        assert "explanation" in data, "Should contain explanation"
        assert "tables_analyzed" in data, "Should contain tables_analyzed"

        # Validate explanation is non-empty
        explanation = data.get("explanation", "")
        assert explanation, "Explanation should not be empty"
        assert len(explanation) > 50, "Explanation should be detailed"

        # Validate tables extracted
        tables = data.get("tables_analyzed", [])
        assert "products" in tables, "Should identify products table"

        api_test_logger.info(f"Explanation: {explanation[:200]}...")
        api_test_logger.info(f"Tables analyzed: {tables}")

    def test_explain_complex_join_query(self, api_client, api_test_logger):
        """Test explaining a complex query with joins"""
        api_test_logger.info("Testing /sql/explain with JOIN query")

        payload = {
            "sql": """
                SELECT u.user_id, u.first_name, COUNT(o.order_id) as order_count
                FROM users u
                LEFT JOIN orders o ON u.user_id = o.user_id
                WHERE u.created_at >= '2023-01-01'
                GROUP BY u.user_id, u.first_name
                HAVING COUNT(o.order_id) > 5
                ORDER BY order_count DESC
            """
        }

        response = api_client.post("/sql/explain", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

        explanation = data.get("explanation", "")
        assert "join" in explanation.lower() or "JOIN" in explanation, \
            "Explanation should mention the join"

        # Should identify both tables
        tables = data.get("tables_analyzed", [])
        assert len(tables) >= 2, "Should identify multiple tables"

    def test_explain_aggregation_query(self, api_client, api_test_logger):
        """Test explaining aggregation with GROUP BY"""
        api_test_logger.info("Testing /sql/explain with aggregation")

        payload = {
            "sql": "SELECT gender, AVG(age) as avg_age, COUNT(*) as count FROM users GROUP BY gender"
        }

        response = api_client.post("/sql/explain", json=payload)
        assert response.status_code == 200

        data = response.json()
        explanation = data.get("explanation", "").lower()

        # Explanation should mention aggregation concepts
        assert "group" in explanation or "average" in explanation or "count" in explanation, \
            "Explanation should describe aggregation"


@pytest.mark.api
@pytest.mark.slow
class TestSQLCompleteEndpoint:
    """Test suite for POST /sql/complete endpoint"""

    def test_complete_table_name(self, api_client, api_test_logger):
        """Test autocomplete for table name"""
        api_test_logger.info("Testing /sql/complete for table name")

        payload = {
            "partial_sql": "SELECT * FROM us",
            "cursor_position": {"line": 0, "column": 18}  # After "us"
        }

        response = api_client.post("/sql/complete", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True, f"Complete should succeed: {data.get('error')}"

        # Validate response structure
        assert "suggestions" in data, "Should contain suggestions"
        suggestions = data.get("suggestions", [])

        assert len(suggestions) > 0, "Should return at least one suggestion"

        # Validate suggestion structure
        for suggestion in suggestions:
            assert "completion" in suggestion, "Suggestion should have completion"
            assert "explanation" in suggestion, "Suggestion should have explanation"

        api_test_logger.info(f"Returned {len(suggestions)} suggestions")
        api_test_logger.info(f"First suggestion: {suggestions[0].get('completion')}")

    def test_complete_column_name(self, api_client, api_test_logger):
        """Test autocomplete for column name"""
        api_test_logger.info("Testing /sql/complete for column name")

        payload = {
            "partial_sql": "SELECT user_id, fir FROM users",
            "cursor_position": {"line": 0, "column": 19}  # After "fir"
        }

        response = api_client.post("/sql/complete", json=payload)
        assert response.status_code == 200

        data = response.json()
        suggestions = data.get("suggestions", [])

        if suggestions:
            api_test_logger.info(f"Column suggestions: {[s['completion'] for s in suggestions[:3]]}")

    def test_complete_join_clause(self, api_client, api_test_logger):
        """Test autocomplete for JOIN clause"""
        api_test_logger.info("Testing /sql/complete for JOIN")

        payload = {
            "partial_sql": "SELECT * FROM users u JOIN ",
            "cursor_position": {"line": 0, "column": 31}  # After "JOIN "
        }

        response = api_client.post("/sql/complete", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


@pytest.mark.api
@pytest.mark.slow
class TestSQLFixEndpoint:
    """Test suite for POST /sql/fix endpoint"""

    def test_fix_wrong_table_name(self, api_client, api_test_logger):
        """Test fixing query with wrong table name"""
        api_test_logger.info("Testing /sql/fix for wrong table name")

        payload = {
            "sql": "SELECT * FROM usersss WHERE age > 25",  # Wrong table name
            "error_message": "Table not found: usersss"
        }

        response = api_client.post("/sql/fix", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True, f"Fix should succeed: {data.get('error')}"

        # Validate response structure
        assert "diagnosis" in data, "Should contain diagnosis"
        assert "fixed_sql" in data, "Should contain fixed_sql"
        assert "changes" in data, "Should contain changes explanation"

        # Validate diagnosis is provided
        diagnosis = data.get("diagnosis", "")
        assert diagnosis, "Should provide diagnosis"

        # Validate fixed SQL is provided
        fixed_sql = data.get("fixed_sql", "")
        assert fixed_sql, "Should provide fixed SQL"

        api_test_logger.info(f"Diagnosis: {diagnosis[:100]}...")
        api_test_logger.info(f"Fixed SQL: {fixed_sql[:100]}...")

    def test_fix_missing_comma(self, api_client, api_test_logger):
        """Test fixing syntax error (missing comma)"""
        api_test_logger.info("Testing /sql/fix for missing comma")

        payload = {
            "sql": "SELECT user_id first_name last_name FROM users",  # Missing commas
            "error_message": "Syntax error: Expected end of input but got identifier"
        }

        response = api_client.post("/sql/fix", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

        fixed_sql = data.get("fixed_sql", "")
        assert fixed_sql, "Should provide fixed SQL"

        # Fixed SQL should have commas
        assert "," in fixed_sql, "Fixed SQL should include commas"

    def test_fix_mismatched_parentheses(self, api_client, api_test_logger):
        """Test fixing mismatched parentheses"""
        api_test_logger.info("Testing /sql/fix for mismatched parentheses")

        payload = {
            "sql": "SELECT COUNT( FROM users",  # Missing closing parenthesis
            "error_message": "Syntax error: Unexpected end of statement"
        }

        response = api_client.post("/sql/fix", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

        changes = data.get("changes", "")
        assert changes, "Should explain what was changed"

    def test_fix_wrong_column_reference(self, api_client, api_test_logger):
        """Test fixing query with wrong column name"""
        api_test_logger.info("Testing /sql/fix for wrong column")

        payload = {
            "sql": "SELECT user_id, invalid_column_xyz FROM users",
            "error_message": "Column invalid_column_xyz not found in table users"
        }

        response = api_client.post("/sql/fix", json=payload)
        assert response.status_code == 200

        data = response.json()
        diagnosis = data.get("diagnosis", "")

        # Should identify the problem
        assert "column" in diagnosis.lower(), "Diagnosis should mention column issue"


@pytest.mark.api
class TestSQLFormatEndpoint:
    """Test suite for POST /sql/format endpoint (uses sqlparse, no LLM)"""

    def test_format_unformatted_query(self, api_client, api_test_logger):
        """Test formatting an unformatted SQL query"""
        api_test_logger.info("Testing /sql/format with unformatted SQL")

        payload = {
            "sql": "select user_id,first_name,last_name from users where age>25 order by last_name"
        }

        response = api_client.post("/sql/format", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True, f"Format should succeed: {data.get('error')}"

        # Validate response structure
        assert "formatted_sql" in data, "Should contain formatted_sql"

        formatted = data.get("formatted_sql", "")
        assert formatted, "Formatted SQL should not be empty"

        # Formatted SQL should have uppercase keywords
        assert "SELECT" in formatted, "Keywords should be uppercase"
        assert "FROM" in formatted, "Keywords should be uppercase"
        assert "WHERE" in formatted, "Keywords should be uppercase"

        # Should have better formatting (line breaks, indentation)
        assert "\n" in formatted, "Should have line breaks"

        api_test_logger.info("Original SQL:")
        api_test_logger.info(f"  {payload['sql']}")
        api_test_logger.info("Formatted SQL:")
        api_test_logger.info(f"  {formatted}")

    def test_format_already_formatted_query(self, api_client):
        """Test that already formatted query is handled correctly"""
        payload = {
            "sql": """SELECT
  user_id,
  first_name
FROM
  users
WHERE
  age > 25"""
        }

        response = api_client.post("/sql/format", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data.get("formatted_sql"), "Should still return formatted SQL"

    def test_format_complex_query_with_joins(self, api_client):
        """Test formatting complex query with joins"""
        payload = {
            "sql": "select u.user_id,u.name,count(o.order_id) from users u left join orders o on u.user_id=o.user_id group by u.user_id,u.name"
        }

        response = api_client.post("/sql/format", json=payload)
        assert response.status_code == 200

        data = response.json()
        formatted = data.get("formatted_sql", "")

        # Should format JOIN keyword
        assert "JOIN" in formatted, "Should uppercase JOIN"
        assert "GROUP BY" in formatted, "Should uppercase GROUP BY"

    def test_format_handles_invalid_sql_gracefully(self, api_client):
        """Test that formatter handles invalid SQL without crashing"""
        payload = {
            "sql": "SELECT * FROM WHERE AND"  # Invalid SQL
        }

        response = api_client.post("/sql/format", json=payload)
        assert response.status_code == 200

        # Should either format it as-is or return error
        data = response.json()
        assert "success" in data


@pytest.mark.api
@pytest.mark.slow
class TestSQLChatEndpoint:
    """Test suite for POST /sql/chat endpoint"""

    def test_chat_about_current_sql(self, api_client, api_test_logger):
        """Test conversational assistance about current SQL"""
        api_test_logger.info("Testing /sql/chat with question about SQL")

        payload = {
            "sql": "SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id",
            "messages": [
                {"role": "user", "content": "What does this query do?"}
            ]
        }

        response = api_client.post("/sql/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True, f"Chat should succeed: {data.get('error')}"

        # Validate response structure
        assert "reply" in data, "Should contain reply"
        assert "tables" in data, "Should contain tables analyzed"

        reply = data.get("reply", "")
        assert reply, "Reply should not be empty"
        assert len(reply) > 20, "Reply should be meaningful"

        api_test_logger.info(f"Chat reply: {reply[:200]}...")

    def test_chat_optimization_suggestion(self, api_client, api_test_logger):
        """Test asking for optimization suggestions"""
        api_test_logger.info("Testing /sql/chat for optimization")

        payload = {
            "sql": "SELECT * FROM users WHERE email LIKE '%@example.com'",
            "messages": [
                {"role": "user", "content": "How can I optimize this query?"}
            ]
        }

        response = api_client.post("/sql/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        reply = data.get("reply", "")

        # Reply should provide suggestions
        assert reply, "Should provide optimization suggestions"

    def test_chat_multi_turn_conversation(self, api_client, api_test_logger):
        """Test multi-turn conversation"""
        api_test_logger.info("Testing /sql/chat with multi-turn conversation")

        payload = {
            "sql": "SELECT product_id, name FROM products",
            "messages": [
                {"role": "user", "content": "What does this query do?"},
                {"role": "assistant", "content": "This query retrieves product IDs and names from the products table."},
                {"role": "user", "content": "How do I add a price filter?"}
            ]
        }

        response = api_client.post("/sql/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

        reply = data.get("reply", "")
        assert reply, "Should handle multi-turn conversation"

        # Reply should mention WHERE or filtering
        assert "where" in reply.lower() or "filter" in reply.lower(), \
            "Should provide relevant answer about filtering"

    def test_chat_with_empty_messages_fails_validation(self, api_client):
        """Test that empty messages list fails validation"""
        payload = {
            "sql": "SELECT * FROM users",
            "messages": []  # Empty messages
        }

        response = api_client.post("/sql/chat", json=payload)

        # Should return validation error
        assert response.status_code == 422, \
            f"Expected 422 for empty messages, got {response.status_code}"

    def test_chat_identifies_tables(self, api_client):
        """Test that chat correctly identifies tables in SQL"""
        payload = {
            "sql": "SELECT u.user_id, o.order_id FROM users u JOIN orders o ON u.user_id = o.user_id",
            "messages": [
                {"role": "user", "content": "What tables are being used?"}
            ]
        }

        response = api_client.post("/sql/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        tables = data.get("tables", [])

        # Should identify the tables
        assert len(tables) > 0, "Should identify tables from SQL"
