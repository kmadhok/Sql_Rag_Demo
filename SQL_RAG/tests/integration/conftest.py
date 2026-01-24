#!/usr/bin/env python3
"""
Integration Test Configuration
Provides fixtures for TRUE end-to-end testing with real components (no mocks)
"""

import os
import sys
import pytest
import yaml
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "rag_app"))

# Check for required dependencies
try:
    from langchain_community.vectorstores import FAISS
    from gemini_client import GeminiClient
    from bigquery_client import BigQueryClient
    from schema_manager import SchemaManager
    from utils.embedding_provider import get_embedding_function
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    IMPORT_ERROR = str(e)


# ============================================================================
# Environment Validation
# ============================================================================

def check_api_keys():
    """Check if required API keys are available"""
    missing = []

    if not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if not os.getenv("GEMINI_API_KEY"):
        missing.append("GEMINI_API_KEY")

    return missing


def check_bigquery_credentials():
    """Check if BigQuery credentials are available"""
    # BigQuery can use:
    # 1. GOOGLE_APPLICATION_CREDENTIALS env var
    # 2. Default credentials from gcloud
    # 3. Service account key file

    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return True

    # Try to detect gcloud default credentials
    try:
        from google.auth import default
        credentials, project = default()
        return True
    except Exception:
        return False


# ============================================================================
# Session-scoped Fixtures (expensive, load once)
# ============================================================================

@pytest.fixture(scope="session")
def integration_skip_reason():
    """Determine if integration tests should be skipped and why"""
    if not DEPENDENCIES_AVAILABLE:
        return f"Missing dependencies: {IMPORT_ERROR}"

    missing_keys = check_api_keys()
    if missing_keys:
        return f"Missing API keys: {', '.join(missing_keys)}. Set in .env or environment."

    if not check_bigquery_credentials():
        return "BigQuery credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS or run 'gcloud auth application-default login'"

    return None


@pytest.fixture(scope="session")
def test_questions():
    """Load test questions from YAML file"""
    yaml_path = Path(__file__).parent / "test_questions.yaml"

    if not yaml_path.exists():
        pytest.skip(f"Test questions file not found: {yaml_path}")

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    return data.get("test_cases", [])


@pytest.fixture(scope="session")
def test_vector_store_path():
    """Path to the test vector store (created by setup script)"""
    # Integration tests should use a dedicated test vector store
    # located at tests/integration/test_vector_store/
    test_store_path = Path(__file__).parent / "test_vector_store"

    if not test_store_path.exists():
        pytest.skip(
            f"Test vector store not found at {test_store_path}.\n"
            "Run setup script first: python tests/integration/setup_test_vector_store.py"
        )

    return str(test_store_path)


@pytest.fixture(scope="session")
def embedding_function():
    """Real OpenAI embedding function (not mocked)"""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    return get_embedding_function(provider="openai")


@pytest.fixture(scope="session")
def vector_store(test_vector_store_path, embedding_function):
    """Real FAISS vector store loaded from disk (not mocked)"""
    try:
        store = FAISS.load_local(
            test_vector_store_path,
            embedding_function,
            allow_dangerous_deserialization=True
        )
        return store
    except Exception as e:
        pytest.skip(f"Failed to load vector store: {e}")


@pytest.fixture(scope="session")
def schema_manager():
    """Real SchemaManager with actual schema data (not mocked)"""
    schema_path = project_root / "rag_app" / "data_new" / "thelook_ecommerce_schema.csv"

    if not schema_path.exists():
        pytest.skip(f"Schema file not found: {schema_path}")

    return SchemaManager(str(schema_path))


@pytest.fixture(scope="session")
def gemini_client():
    """Real Gemini client (not mocked)"""
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    try:
        client = GeminiClient(
            api_key=os.getenv("GEMINI_API_KEY"),
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        )
        return client
    except Exception as e:
        pytest.skip(f"Failed to create Gemini client: {e}")


@pytest.fixture(scope="session")
def bigquery_client():
    """Real BigQuery client (not mocked)"""
    if not check_bigquery_credentials():
        pytest.skip("BigQuery credentials not found")

    try:
        client = BigQueryClient(
            project_id=os.getenv("GCP_PROJECT_ID", "brainrot-453319"),
            max_bytes_billed=100_000_000  # 100MB limit for safety
        )
        return client
    except Exception as e:
        pytest.skip(f"Failed to create BigQuery client: {e}")


# ============================================================================
# Function-scoped Fixtures (per-test)
# ============================================================================

@pytest.fixture
def test_results_logger(tmp_path):
    """Logger for capturing test results and debugging info"""
    log_file = tmp_path / "integration_test_results.log"

    import logging
    logger = logging.getLogger("integration_tests")
    logger.setLevel(logging.INFO)

    # File handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    yield logger

    # Print log file location at end of test
    print(f"\nIntegration test logs: {log_file}")


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers",
        "integration: True integration tests (real APIs, real DB, no mocks)"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip integration tests if requirements not met"""
    skip_reason = None

    # Check dependencies
    if not DEPENDENCIES_AVAILABLE:
        skip_reason = f"Missing dependencies: {IMPORT_ERROR}"
    else:
        # Check credentials
        missing_keys = check_api_keys()
        if missing_keys:
            skip_reason = f"Missing API keys: {', '.join(missing_keys)}"
        elif not check_bigquery_credentials():
            skip_reason = "BigQuery credentials not found"

    if skip_reason:
        skip_marker = pytest.mark.skip(reason=skip_reason)
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_marker)
