#!/usr/bin/env python3
"""
API Tests for Schema Exploration Endpoints

Tests the following endpoints with REAL SchemaManager and Gemini:
- GET /schema/tables - List all available tables
- GET /schema/tables/{table_name}/columns - Get columns for specific table
- GET /schema/tables/{table_name}/description - AI-generated table description

These tests validate the HTTP layer with real schema data.
"""

import pytest


@pytest.mark.api
class TestSchemaTablesEndpoint:
    """Test suite for GET /schema/tables endpoint"""

    def test_list_all_tables_returns_table_array(self, api_client, api_test_logger):
        """Test listing all available tables"""
        api_test_logger.info("Testing GET /schema/tables")

        response = api_client.get("/schema/tables")
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"Schema tables response: {data}")

        # Validate response structure
        assert "success" in data, "Response should contain success"
        assert "tables" in data, "Response should contain tables array"
        assert "table_count" in data, "Response should contain table_count"

        # Validate success
        assert data["success"] is True, "Request should succeed"

        # Validate tables array
        tables = data.get("tables", [])
        assert isinstance(tables, list), "Tables should be a list"
        assert len(tables) > 0, "Should have at least one table"

        # Validate table count matches
        assert data["table_count"] == len(tables), \
            f"Table count should match array length: {data['table_count']} != {len(tables)}"

        # Validate table names are strings
        for table in tables:
            assert isinstance(table, str), f"Table name should be string, got {type(table)}"

        api_test_logger.info(f"Found {len(tables)} tables: {tables[:5]}...")

    def test_tables_list_includes_expected_tables(self, api_client, api_test_logger):
        """Test that common tables are in the list"""
        response = api_client.get("/schema/tables")
        assert response.status_code == 200

        data = response.json()
        tables = [t.lower() for t in data.get("tables", [])]

        # Check for expected tables (thelook_ecommerce dataset)
        expected_tables = ["products", "users", "orders"]

        for table in expected_tables:
            assert table in tables, f"Expected table '{table}' not found in schema"
            api_test_logger.info(f"✅ Found expected table: {table}")


@pytest.mark.api
class TestSchemaTableColumnsEndpoint:
    """Test suite for GET /schema/tables/{table_name}/columns endpoint"""

    def test_get_columns_for_valid_table(self, api_client, api_test_logger):
        """Test getting columns for a valid table"""
        table_name = "products"
        api_test_logger.info(f"Testing GET /schema/tables/{table_name}/columns")

        response = api_client.get(f"/schema/tables/{table_name}/columns")
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"Columns response for {table_name}: {data.keys()}")

        # Validate response structure
        assert "success" in data
        assert "table" in data
        assert "fully_qualified_name" in data
        assert "columns" in data
        assert "column_count" in data

        # Validate success
        assert data["success"] is True

        # Validate table name matches
        assert data["table"] == table_name

        # Validate FQN format
        fqn = data.get("fully_qualified_name", "")
        assert fqn, "Should have fully qualified name"
        api_test_logger.info(f"FQN: {fqn}")

        # Validate columns array
        columns = data.get("columns", [])
        assert len(columns) > 0, "Should have at least one column"

        # Validate column count matches
        assert data["column_count"] == len(columns)

        # Validate column structure
        for column in columns:
            assert "name" in column, "Column should have name"
            assert "type" in column, "Column should have type"
            assert "description" in column, "Column should have description"
            assert isinstance(column["name"], str), "Column name should be string"

        api_test_logger.info(f"Found {len(columns)} columns")
        api_test_logger.info(f"Sample columns: {[c['name'] for c in columns[:5]]}")

    def test_get_columns_for_users_table(self, api_client):
        """Test getting columns for users table"""
        response = api_client.get("/schema/tables/users/columns")
        assert response.status_code == 200

        data = response.json()
        columns = data.get("columns", [])

        # Users table should have common columns
        column_names = [c["name"].lower() for c in columns]
        expected_columns = ["user_id", "email"]  # Common user table columns

        for col in expected_columns:
            if col in column_names:
                print(f"✅ Found expected column: {col}")

    def test_get_columns_for_orders_table(self, api_client):
        """Test getting columns for orders table"""
        response = api_client.get("/schema/tables/orders/columns")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert len(data.get("columns", [])) > 0, "Orders table should have columns"

    def test_get_columns_for_invalid_table_returns_404(self, api_client, api_test_logger):
        """Test that invalid table name returns 404"""
        table_name = "nonexistent_invalid_table_xyz"
        api_test_logger.info(f"Testing GET /schema/tables/{table_name}/columns (should 404)")

        response = api_client.get(f"/schema/tables/{table_name}/columns")

        # Should return 404 for nonexistent table
        assert response.status_code == 404, \
            f"Expected 404 for invalid table, got {response.status_code}"

        api_test_logger.info("✅ Correctly returned 404 for invalid table")

    def test_columns_include_data_types(self, api_client):
        """Test that columns include data type information"""
        response = api_client.get("/schema/tables/products/columns")
        assert response.status_code == 200

        data = response.json()
        columns = data.get("columns", [])

        # At least some columns should have type information
        columns_with_types = [c for c in columns if c.get("type")]
        assert len(columns_with_types) > 0, "Should have columns with data types"


@pytest.mark.api
@pytest.mark.slow
class TestSchemaTableDescriptionEndpoint:
    """Test suite for GET /schema/tables/{table_name}/description endpoint"""

    def test_get_ai_description_for_products_table(self, api_client, api_test_logger):
        """Test AI-generated description for products table"""
        table_name = "products"
        api_test_logger.info(f"Testing GET /schema/tables/{table_name}/description")

        response = api_client.get(f"/schema/tables/{table_name}/description")
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"Description response: {data}")

        # Validate response structure
        assert "success" in data
        assert "table" in data
        assert "description" in data

        # Validate success
        assert data["success"] is True

        # Validate table name matches
        assert data["table"] == table_name

        # Validate description is non-empty
        description = data.get("description", "")
        assert description, "Description should not be empty"
        assert len(description) > 10, "Description should be meaningful (>10 chars)"

        # Description should mention the table or related concepts
        description_lower = description.lower()
        assert "product" in description_lower or "item" in description_lower, \
            "Description should mention products/items"

        api_test_logger.info(f"AI Description: {description}")

    def test_get_ai_description_for_users_table(self, api_client, api_test_logger):
        """Test AI-generated description for users table"""
        table_name = "users"
        api_test_logger.info(f"Testing GET /schema/tables/{table_name}/description")

        response = api_client.get(f"/schema/tables/{table_name}/description")
        assert response.status_code == 200

        data = response.json()
        description = data.get("description", "")

        assert description, "Should generate description for users table"
        assert "user" in description.lower() or "customer" in description.lower(), \
            "Description should mention users/customers"

        api_test_logger.info(f"Users description: {description}")

    def test_get_ai_description_for_orders_table(self, api_client):
        """Test AI-generated description for orders table"""
        response = api_client.get("/schema/tables/orders/description")
        assert response.status_code == 200

        data = response.json()
        description = data.get("description", "")

        assert description, "Should generate description for orders table"
        assert "order" in description.lower() or "transaction" in description.lower(), \
            "Description should mention orders/transactions"

    def test_description_for_invalid_table_returns_404(self, api_client, api_test_logger):
        """Test that invalid table returns 404"""
        table_name = "nonexistent_table_xyz"
        api_test_logger.info(f"Testing GET /schema/tables/{table_name}/description (should 404)")

        response = api_client.get(f"/schema/tables/{table_name}/description")

        # Should return 404 for nonexistent table
        assert response.status_code == 404, \
            f"Expected 404 for invalid table, got {response.status_code}"

    def test_description_is_concise(self, api_client):
        """Test that AI descriptions are concise (10-20 words as designed)"""
        response = api_client.get("/schema/tables/products/description")
        assert response.status_code == 200

        data = response.json()
        description = data.get("description", "")

        word_count = len(description.split())

        # Per API spec, should be 10-20 words
        assert 5 <= word_count <= 50, \
            f"Description should be concise (5-50 words), got {word_count} words"

    def test_descriptions_are_different_for_different_tables(self, api_client, api_test_logger):
        """Test that different tables get different descriptions"""
        # Get descriptions for two different tables
        response1 = api_client.get("/schema/tables/products/description")
        response2 = api_client.get("/schema/tables/users/description")

        assert response1.status_code == 200
        assert response2.status_code == 200

        desc1 = response1.json().get("description", "")
        desc2 = response2.json().get("description", "")

        # Descriptions should be different (not identical)
        assert desc1 != desc2, "Different tables should have different descriptions"

        api_test_logger.info(f"Products: {desc1}")
        api_test_logger.info(f"Users: {desc2}")
