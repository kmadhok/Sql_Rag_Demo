#!/usr/bin/env python3
"""
Shared fixtures for API endpoint tests

Provides:
- FastAPI TestClient for making HTTP requests
- Cleanup fixtures for test data (saved queries, dashboards)
- Factory fixtures for creating test entities
- Sample data fixtures for common payloads
- Logging fixtures for test execution tracking

These tests use REAL services (no mocks):
- Real FAISS vector store
- Real Gemini API
- Real BigQuery executor
- Real Firestore storage
"""

import pytest
import logging
from typing import Dict, Any, Set
from datetime import datetime


# =============================================================================
# Session-level Configuration
# =============================================================================

@pytest.fixture(scope="session")
def api_skip_reason():
    """
    Check prerequisites for API tests.
    Returns None if tests can run, otherwise returns skip reason.
    """
    import os
    
    # Check for required API keys
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        return "API tests require GEMINI_API_KEY or OPENAI_API_KEY"
    
    # Check that FastAPI app exists
    try:
        from api.main import app
    except ImportError:
        return "FastAPI app not found - ensure api/main.py exists"
    
    return None


@pytest.fixture(scope="session")
def api_client(api_skip_reason):
    """
    FastAPI TestClient for making HTTP requests to the API.
    
    Uses real backend services:
    - FAISS vector store
    - Gemini/OpenAI LLM
    - BigQuery executor
    - Firestore storage
    
    Yields:
        TestClient: FastAPI test client instance
    """
    if api_skip_reason:
        pytest.skip(api_skip_reason)
    
    from fastapi.testclient import TestClient
    from api.main import app
    
    with TestClient(app) as client:
        yield client


# =============================================================================
# Logging Fixtures
# =============================================================================

@pytest.fixture
def api_test_logger():
    """Logger for API test execution"""
    logger = logging.getLogger("api_tests")
    logger.setLevel(logging.INFO)
    return logger


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_saved_query_data():
    """Sample saved query payload for testing"""
    return {
        "question": "What are the top 10 most expensive products?",
        "sql": "SELECT product_id, name, retail_price FROM `bigquery-public-data.thelook_ecommerce.products` ORDER BY retail_price DESC LIMIT 10",
        "data": [
            {"product_id": 1, "name": "Product A", "retail_price": 199.99},
            {"product_id": 2, "name": "Product B", "retail_price": 149.99},
            {"product_id": 3, "name": "Product C", "retail_price": 129.99},
        ]
    }


@pytest.fixture
def sample_dashboard_data():
    """Sample dashboard payload for testing"""
    return {
        "name": "Test Dashboard - Sales Analysis",
        "layout_items": [
            {
                "i": "chart-1",
                "x": 0,
                "y": 0,
                "w": 6,
                "h": 4,
                "saved_query_id": "test-query-id-1",
                "chart_type": "bar"
            },
            {
                "i": "chart-2",
                "x": 6,
                "y": 0,
                "w": 6,
                "h": 4,
                "saved_query_id": "test-query-id-2",
                "chart_type": "line"
            }
        ]
    }


# =============================================================================
# Cleanup Fixtures (for test data management)
# =============================================================================

@pytest.fixture
def cleanup_test_saved_queries(api_client):
    """
    Track saved queries created during tests and clean them up afterward.
    
    Usage:
        def test_example(api_client, cleanup_test_saved_queries):
            response = api_client.post("/saved_queries", json=data)
            query_id = response.json()["id"]
            cleanup_test_saved_queries.add(query_id)
            # Query will be auto-deleted after test
    
    Yields:
        Set[str]: Set to add query IDs for cleanup
    """
    query_ids: Set[str] = set()
    
    yield query_ids
    
    # Cleanup: Delete all tracked queries
    for query_id in query_ids:
        try:
            # Note: saved queries endpoint might not have DELETE
            # This is a placeholder - adjust based on actual API
            pass
        except Exception as e:
            logging.warning(f"Failed to cleanup saved query {query_id}: {e}")


@pytest.fixture
def cleanup_test_dashboards(api_client):
    """
    Track dashboards created during tests and clean them up afterward.
    
    Usage:
        def test_example(api_client, cleanup_test_dashboards):
            response = api_client.post("/dashboards", json=data)
            dashboard_id = response.json()["id"]
            cleanup_test_dashboards.add(dashboard_id)
            # Dashboard will be auto-deleted after test
    
    Yields:
        Set[str]: Set to add dashboard IDs for cleanup
    """
    dashboard_ids: Set[str] = set()
    
    yield dashboard_ids
    
    # Cleanup: Delete all tracked dashboards
    for dashboard_id in dashboard_ids:
        try:
            api_client.delete(f"/dashboards/{dashboard_id}")
        except Exception as e:
            logging.warning(f"Failed to cleanup dashboard {dashboard_id}: {e}")


# =============================================================================
# Factory Fixtures (for creating test entities)
# =============================================================================

@pytest.fixture
def create_test_saved_query(api_client, cleanup_test_saved_queries, sample_saved_query_data):
    """
    Factory fixture to create saved queries with auto-cleanup.
    
    Usage:
        def test_example(create_test_saved_query):
            query_id = create_test_saved_query()
            # Query is created and will be auto-deleted
            
            # Or with custom data:
            query_id = create_test_saved_query({"question": "Custom query", ...})
    
    Returns:
        Callable: Function that creates saved query and returns ID
    """
    def _create(custom_data: Dict[str, Any] = None) -> str:
        """
        Create a saved query and return its ID.
        
        Args:
            custom_data: Optional custom payload. If None, uses sample_saved_query_data.
        
        Returns:
            str: The created query ID
        """
        data = custom_data if custom_data is not None else sample_saved_query_data
        
        response = api_client.post("/saved_queries", json=data)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create saved query: {response.status_code} - {response.text}")
        
        query_id = response.json()["id"]
        cleanup_test_saved_queries.add(query_id)
        
        return query_id
    
    return _create


@pytest.fixture
def create_test_dashboard(api_client, cleanup_test_dashboards, sample_dashboard_data):
    """
    Factory fixture to create dashboards with auto-cleanup.
    
    Usage:
        def test_example(create_test_dashboard):
            dashboard_id = create_test_dashboard()
            # Dashboard is created and will be auto-deleted
            
            # Or with custom data:
            dashboard_id = create_test_dashboard({"name": "Custom Dashboard", ...})
    
    Returns:
        Callable: Function that creates dashboard and returns ID
    """
    def _create(custom_data: Dict[str, Any] = None) -> str:
        """
        Create a dashboard and return its ID.
        
        Args:
            custom_data: Optional custom payload. If None, uses sample_dashboard_data.
        
        Returns:
            str: The created dashboard ID
        """
        data = custom_data if custom_data is not None else sample_dashboard_data
        
        response = api_client.post("/dashboards", json=data)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create dashboard: {response.status_code} - {response.text}")
        
        dashboard_id = response.json()["id"]
        cleanup_test_dashboards.add(dashboard_id)
        
        return dashboard_id
    
    return _create


# =============================================================================
# Test Execution Helpers
# =============================================================================

@pytest.fixture(autouse=True)
def log_test_execution(request, api_test_logger):
    """Automatically log test start and finish"""
    test_name = request.node.name
    api_test_logger.info(f"▶️  Starting test: {test_name}")
    
    yield
    
    api_test_logger.info(f"✅ Completed test: {test_name}")
