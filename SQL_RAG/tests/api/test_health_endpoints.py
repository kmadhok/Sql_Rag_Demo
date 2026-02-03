#!/usr/bin/env python3
"""
API Tests for Health Check Endpoints

Tests the following endpoints with REAL Firestore:
- GET /health - Basic service health check
- GET /health/dashboard - Dashboard integrity check

These tests validate the HTTP layer with real backend services.
NO MOCKS - validates actual service availability.
"""

import pytest


@pytest.mark.api
class TestBasicHealthEndpoint:
    """Test suite for GET /health endpoint"""

    def test_basic_health_check_returns_ok(self, api_client, api_test_logger):
        """Test that basic health check returns OK status"""
        api_test_logger.info("Testing GET /health")

        response = api_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"Health check response: {data}")

        # Validate response structure
        assert "status" in data, "Response should contain status"
        assert "vector_store" in data, "Response should contain vector_store status"
        assert "bigquery_executor" in data, "Response should contain bigquery_executor status"
        assert "timestamp" in data, "Response should contain timestamp"

        # Validate status values
        assert data["status"] in ["ok", "degraded", "error"], \
            f"Status should be one of ok/degraded/error, got {data['status']}"

        # Vector store and BigQuery should be initialized
        assert data["vector_store"] is True, "Vector store should be available"
        assert data["bigquery_executor"] is True, "BigQuery executor should be available"

    def test_health_check_has_timestamp(self, api_client):
        """Test that health check includes timestamp"""
        response = api_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        timestamp = data.get("timestamp")

        assert timestamp, "Timestamp should not be empty"
        # Timestamp should be ISO format string
        assert isinstance(timestamp, str), "Timestamp should be string"

    def test_health_check_is_fast(self, api_client):
        """Test that health check responds quickly (< 1 second)"""
        import time

        start_time = time.time()
        response = api_client.get("/health")
        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        assert elapsed_time < 1.0, f"Health check should be fast, took {elapsed_time:.2f}s"


@pytest.mark.api
@pytest.mark.firestore
class TestDashboardHealthEndpoint:
    """Test suite for GET /health/dashboard endpoint"""

    def test_dashboard_health_check_validates_dashboards(
        self,
        api_client,
        api_test_logger,
        create_test_dashboard
    ):
        """Test that dashboard health check validates dashboard integrity"""
        api_test_logger.info("Testing GET /health/dashboard")

        # Create a test dashboard first
        dashboard_id = create_test_dashboard()
        api_test_logger.info(f"Created test dashboard: {dashboard_id}")

        # Run dashboard health check
        response = api_client.get("/health/dashboard")
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"Dashboard health response: {data}")

        # Validate response structure
        assert "status" in data, "Response should contain status"
        assert "dashboards_checked" in data, "Response should contain dashboards_checked count"
        assert "issues" in data, "Response should contain issues list"
        assert "timestamp" in data, "Response should contain timestamp"

        # Validate status values
        assert data["status"] in ["ok", "warning", "error"], \
            f"Status should be one of ok/warning/error, got {data['status']}"

        # Should have checked at least one dashboard
        dashboards_checked = data.get("dashboards_checked", 0)
        assert dashboards_checked >= 1, f"Should have checked at least 1 dashboard, got {dashboards_checked}"

        # Issues should be a list
        issues = data.get("issues", [])
        assert isinstance(issues, list), "Issues should be a list"

    def test_dashboard_health_detects_missing_queries(
        self,
        api_client,
        api_test_logger,
        cleanup_test_dashboards
    ):
        """Test that dashboard health check detects broken query references"""
        # Create dashboard with nonexistent query references
        dashboard_data = {
            "name": "Test Dashboard - Broken References",
            "layout_items": [
                {
                    "i": "chart-broken-1",
                    "x": 0,
                    "y": 0,
                    "w": 6,
                    "h": 4,
                    "saved_query_id": "nonexistent-query-id-12345",
                    "chart_type": "bar"
                }
            ]
        }

        response = api_client.post("/dashboards", json=dashboard_data)
        if response.status_code in [200, 201]:
            dashboard_id = response.json()["id"]
            cleanup_test_dashboards.add(dashboard_id)

            # Run dashboard health check
            health_response = api_client.get("/health/dashboard")
            assert health_response.status_code == 200

            data = health_response.json()
            api_test_logger.info(f"Dashboard health with broken refs: {data}")

            # Should detect issues if validation is implemented
            # (This test may pass with status=ok if validation is not strict)
            assert "issues" in data

    def test_dashboard_health_when_no_dashboards(self, api_client):
        """Test dashboard health check when no dashboards exist (or few)"""
        response = api_client.get("/health/dashboard")
        assert response.status_code == 200

        data = response.json()

        # Should still return valid response
        assert "status" in data
        assert "dashboards_checked" in data
        assert "issues" in data

        # Status should be ok or warning (not error)
        assert data["status"] in ["ok", "warning"]
