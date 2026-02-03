#!/usr/bin/env python3
"""
API Tests for Dashboard Endpoints

Tests the following endpoints with REAL Firestore:
- POST /dashboards - Create new dashboard
- GET /dashboards - List all dashboards
- GET /dashboards/{id} - Get specific dashboard
- PATCH /dashboards/{id} - Update dashboard
- POST /dashboards/{id}/duplicate - Duplicate dashboard
- DELETE /dashboards/{id} - Delete dashboard

These tests validate the HTTP layer with real Firestore storage.
NO MOCKS - validates actual dashboard CRUD operations.
"""

import pytest
import re
from datetime import datetime


@pytest.mark.api
@pytest.mark.firestore
class TestDashboardCRUDEndpoints:
    """Test suite for dashboard CRUD operations"""

    def test_create_dashboard_with_layout(
        self,
        api_client,
        api_test_logger,
        cleanup_test_dashboards,
        sample_dashboard_data
    ):
        """Test creating a new dashboard with layout items"""
        api_test_logger.info("Testing POST /dashboards")

        response = api_client.post("/dashboards", json=sample_dashboard_data)

        # Validate HTTP response
        assert response.status_code in [200, 201], \
            f"Expected 200/201, got {response.status_code}: {response.text}"

        data = response.json()
        api_test_logger.info(f"Created dashboard: {data.get('id')}")

        # Track for cleanup
        dashboard_id = data.get("id")
        cleanup_test_dashboards.add(dashboard_id)

        # Validate response structure
        assert "id" in data, "Response should contain id"
        assert "name" in data, "Response should contain name"
        assert "created_at" in data, "Response should contain created_at"
        assert "updated_at" in data, "Response should contain updated_at"
        assert "layout_items" in data, "Response should contain layout_items"

        # Validate ID is UUID format
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_pattern, dashboard_id), f"ID should be UUID format: {dashboard_id}"

        # Validate name matches
        assert data["name"] == sample_dashboard_data["name"]

        # Validate timestamps are ISO format
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        try:
            datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        except ValueError as e:
            pytest.fail(f"Timestamps should be ISO format: {e}")

        # Validate layout_items
        layout_items = data.get("layout_items", [])
        assert isinstance(layout_items, list), "layout_items should be a list"
        assert len(layout_items) == len(sample_dashboard_data["layout_items"])

    def test_create_dashboard_with_empty_layout(
        self,
        api_client,
        cleanup_test_dashboards
    ):
        """Test creating dashboard with no layout items"""
        payload = {
            "name": "Empty Dashboard Test",
            "layout_items": []
        }

        response = api_client.post("/dashboards", json=payload)
        assert response.status_code in [200, 201]

        data = response.json()
        dashboard_id = data.get("id")
        cleanup_test_dashboards.add(dashboard_id)

        # Should accept empty layout
        assert data.get("layout_items") == []

    def test_create_dashboard_without_layout_items_field(
        self,
        api_client,
        cleanup_test_dashboards
    ):
        """Test creating dashboard without layout_items field"""
        payload = {
            "name": "Minimal Dashboard Test"
            # No layout_items field
        }

        response = api_client.post("/dashboards", json=payload)
        assert response.status_code in [200, 201]

        data = response.json()
        dashboard_id = data.get("id")
        cleanup_test_dashboards.add(dashboard_id)

        # Should default to empty layout
        assert isinstance(data.get("layout_items"), list)

    def test_create_dashboard_with_missing_name_fails_validation(self, api_client):
        """Test that dashboard without name fails validation"""
        payload = {
            # No name field
            "layout_items": []
        }

        response = api_client.post("/dashboards", json=payload)

        # Should return 422 validation error
        assert response.status_code == 422, \
            f"Expected 422 for missing name, got {response.status_code}"

    def test_create_dashboard_with_long_name_fails_validation(self, api_client):
        """Test that dashboard name over 100 chars fails validation"""
        payload = {
            "name": "X" * 101,  # Over 100 character limit
            "layout_items": []
        }

        response = api_client.post("/dashboards", json=payload)

        # Should return 422 validation error
        assert response.status_code == 422, \
            f"Expected 422 for name > 100 chars, got {response.status_code}"

    def test_list_dashboards_returns_summaries(
        self,
        api_client,
        api_test_logger,
        create_test_dashboard
    ):
        """Test listing all dashboards"""
        api_test_logger.info("Testing GET /dashboards")

        # Create a test dashboard first
        dashboard_id = create_test_dashboard()
        api_test_logger.info(f"Created test dashboard: {dashboard_id}")

        # List all dashboards
        response = api_client.get("/dashboards")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list), "Response should be a list"

        api_test_logger.info(f"Found {len(data)} dashboards")

        # Find our test dashboard
        test_dashboard = next((d for d in data if d.get("id") == dashboard_id), None)
        assert test_dashboard is not None, f"Test dashboard {dashboard_id} should be in list"

        # Validate summary structure
        assert "id" in test_dashboard
        assert "name" in test_dashboard
        assert "created_at" in test_dashboard
        assert "updated_at" in test_dashboard
        assert "chart_count" in test_dashboard

        # Summaries should NOT include full layout_items
        assert "layout_items" not in test_dashboard, \
            "Summary should not include full layout_items"

        # Validate chart_count
        chart_count = test_dashboard.get("chart_count")
        assert isinstance(chart_count, int), "chart_count should be integer"

    def test_get_dashboard_by_id_returns_full_detail(
        self,
        api_client,
        api_test_logger,
        create_test_dashboard,
        sample_dashboard_data
    ):
        """Test getting specific dashboard by ID"""
        # Create a test dashboard
        dashboard_id = create_test_dashboard()
        api_test_logger.info(f"Testing GET /dashboards/{dashboard_id}")

        # Get the specific dashboard
        response = api_client.get(f"/dashboards/{dashboard_id}")
        assert response.status_code == 200

        data = response.json()
        api_test_logger.info(f"Retrieved dashboard: {data.keys()}")

        # Validate full detail structure
        assert "id" in data
        assert "name" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "layout_items" in data

        # Validate ID matches
        assert data["id"] == dashboard_id

        # Validate layout_items is present
        layout_items = data.get("layout_items", [])
        assert isinstance(layout_items, list), "Should include full layout_items"

    def test_get_dashboard_with_invalid_id_returns_404(
        self,
        api_client,
        api_test_logger
    ):
        """Test that invalid dashboard ID returns 404"""
        invalid_id = "nonexistent-dashboard-id-12345"
        api_test_logger.info(f"Testing GET /dashboards/{invalid_id} (should 404)")

        response = api_client.get(f"/dashboards/{invalid_id}")

        # Should return 404 for nonexistent dashboard
        assert response.status_code == 404, \
            f"Expected 404 for invalid ID, got {response.status_code}"

    def test_update_dashboard_name(
        self,
        api_client,
        api_test_logger,
        create_test_dashboard
    ):
        """Test updating dashboard name"""
        # Create initial dashboard
        dashboard_id = create_test_dashboard()
        api_test_logger.info(f"Testing PATCH /dashboards/{dashboard_id}")

        # Update name only
        update_payload = {
            "name": "Updated Dashboard Name"
        }

        response = api_client.patch(f"/dashboards/{dashboard_id}", json=update_payload)
        assert response.status_code == 200

        data = response.json()

        # Validate name was updated
        assert data["name"] == "Updated Dashboard Name"

        # Validate updated_at changed
        # (Can't easily compare timestamps, but should be present)
        assert "updated_at" in data

    def test_update_dashboard_layout_items(
        self,
        api_client,
        create_test_dashboard
    ):
        """Test updating dashboard layout items"""
        dashboard_id = create_test_dashboard()

        # Update layout_items
        new_layout = [
            {
                "i": "chart-updated-1",
                "x": 0,
                "y": 0,
                "w": 12,
                "h": 6,
                "saved_query_id": "updated-query-id",
                "chart_type": "line"
            }
        ]

        update_payload = {
            "layout_items": new_layout
        }

        response = api_client.patch(f"/dashboards/{dashboard_id}", json=update_payload)
        assert response.status_code == 200

        data = response.json()

        # Validate layout was updated
        layout_items = data.get("layout_items", [])
        assert len(layout_items) == 1
        assert layout_items[0]["i"] == "chart-updated-1"

    def test_update_dashboard_both_name_and_layout(
        self,
        api_client,
        create_test_dashboard
    ):
        """Test updating both name and layout simultaneously"""
        dashboard_id = create_test_dashboard()

        update_payload = {
            "name": "Completely Updated Dashboard",
            "layout_items": []
        }

        response = api_client.patch(f"/dashboards/{dashboard_id}", json=update_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Completely Updated Dashboard"
        assert data["layout_items"] == []

    def test_update_nonexistent_dashboard_returns_404(self, api_client):
        """Test updating nonexistent dashboard returns 404"""
        invalid_id = "nonexistent-dashboard-12345"

        update_payload = {
            "name": "New Name"
        }

        response = api_client.patch(f"/dashboards/{invalid_id}", json=update_payload)
        assert response.status_code == 404

    def test_duplicate_dashboard_creates_copy(
        self,
        api_client,
        api_test_logger,
        create_test_dashboard,
        cleanup_test_dashboards
    ):
        """Test duplicating a dashboard"""
        # Create original dashboard
        original_id = create_test_dashboard()
        api_test_logger.info(f"Testing POST /dashboards/{original_id}/duplicate")

        # Duplicate it
        response = api_client.post(f"/dashboards/{original_id}/duplicate")
        assert response.status_code in [200, 201]

        data = response.json()
        duplicated_id = data.get("id")

        # Track for cleanup
        cleanup_test_dashboards.add(duplicated_id)

        # Validate new dashboard created
        assert duplicated_id != original_id, "Duplicate should have different ID"

        # Validate name includes "Copy of"
        assert "copy" in data["name"].lower(), "Duplicate should have 'Copy' in name"

        # Validate layout_items copied
        assert "layout_items" in data

    def test_duplicate_nonexistent_dashboard_returns_404(self, api_client):
        """Test duplicating nonexistent dashboard returns 404"""
        invalid_id = "nonexistent-dashboard-12345"

        response = api_client.post(f"/dashboards/{invalid_id}/duplicate")
        assert response.status_code == 404

    def test_delete_dashboard(
        self,
        api_client,
        api_test_logger,
        create_test_dashboard
    ):
        """Test deleting a dashboard"""
        # Create dashboard
        dashboard_id = create_test_dashboard()
        api_test_logger.info(f"Testing DELETE /dashboards/{dashboard_id}")

        # Delete it
        response = api_client.delete(f"/dashboards/{dashboard_id}")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data, "Should return success message"

        # Verify it's deleted - get should return 404
        get_response = api_client.get(f"/dashboards/{dashboard_id}")
        assert get_response.status_code == 404, \
            "Deleted dashboard should return 404"

    def test_delete_nonexistent_dashboard_returns_404(self, api_client):
        """Test deleting nonexistent dashboard returns 404"""
        invalid_id = "nonexistent-dashboard-12345"

        response = api_client.delete(f"/dashboards/{invalid_id}")
        assert response.status_code == 404

    def test_delete_dashboard_is_idempotent(
        self,
        api_client,
        create_test_dashboard
    ):
        """Test that deleting twice returns 404 on second attempt"""
        dashboard_id = create_test_dashboard()

        # First delete
        response1 = api_client.delete(f"/dashboards/{dashboard_id}")
        assert response1.status_code == 200

        # Second delete (should return 404)
        response2 = api_client.delete(f"/dashboards/{dashboard_id}")
        assert response2.status_code == 404, \
            "Deleting already-deleted dashboard should return 404"

    def test_dashboards_persist_across_requests(
        self,
        api_client,
        create_test_dashboard
    ):
        """Test that dashboards persist across multiple requests"""
        dashboard_id = create_test_dashboard()

        # Retrieve it multiple times
        response1 = api_client.get(f"/dashboards/{dashboard_id}")
        response2 = api_client.get(f"/dashboards/{dashboard_id}")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Should return same data
        data1 = response1.json()
        data2 = response2.json()

        assert data1["id"] == data2["id"]
        assert data1["name"] == data2["name"]

    def test_multiple_dashboards_are_independent(
        self,
        api_client,
        cleanup_test_dashboards,
        sample_dashboard_data
    ):
        """Test that multiple dashboards are stored independently"""
        # Create two dashboards
        dashboard1_data = sample_dashboard_data.copy()
        dashboard1_data["name"] = "First Dashboard"

        dashboard2_data = sample_dashboard_data.copy()
        dashboard2_data["name"] = "Second Dashboard"

        response1 = api_client.post("/dashboards", json=dashboard1_data)
        response2 = api_client.post("/dashboards", json=dashboard2_data)

        assert response1.status_code in [200, 201]
        assert response2.status_code in [200, 201]

        dashboard1_id = response1.json()["id"]
        dashboard2_id = response2.json()["id"]

        cleanup_test_dashboards.add(dashboard1_id)
        cleanup_test_dashboards.add(dashboard2_id)

        # IDs should be different
        assert dashboard1_id != dashboard2_id

        # Retrieve both and validate they're different
        get1 = api_client.get(f"/dashboards/{dashboard1_id}").json()
        get2 = api_client.get(f"/dashboards/{dashboard2_id}").json()

        assert get1["name"] == "First Dashboard"
        assert get2["name"] == "Second Dashboard"
