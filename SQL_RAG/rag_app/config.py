#!/usr/bin/env python3
"""
Configuration constants and settings for SQL RAG Streamlit application.
Extracted from app_simple_gemini.py for better modularity.
"""

import os
from pathlib import Path

_BASE_DIR = Path(__file__).parent


def _env_path(key: str, default: Path) -> Path:
    """Resolve a path from environment variables with sensible defaults."""
    value = os.getenv(key)
    if value:
        return Path(value).expanduser()
    return default


# ============================================================================
# File Paths and Directories
# ============================================================================
FAISS_INDICES_DIR = _env_path("FAISS_INDICES_DIR", _BASE_DIR / "faiss_indices")
CSV_PATH = _env_path("CSV_PATH", _BASE_DIR / "sample_queries_with_metadata.csv")  # CSV data source
CATALOG_ANALYTICS_DIR = _env_path("CATALOG_ANALYTICS_DIR", _BASE_DIR / "catalog_analytics")  # Cached analytics
SCHEMA_CSV_PATH = _env_path("SCHEMA_CSV_PATH", _BASE_DIR / "schema.csv")  # Schema file with table_id, column, datatype

# ============================================================================
# Vector Store Configuration
# ============================================================================
DEFAULT_VECTOR_STORE = os.getenv("DEFAULT_VECTOR_STORE") or os.getenv("VECTOR_STORE_NAME") or "index_queries_with_descriptions (1)"  # Expected index name

# ============================================================================
# Pagination Configuration
# ============================================================================
QUERIES_PER_PAGE = 15  # Optimal balance: not too few, not too many for performance
MAX_PAGES_TO_SHOW = 10  # Maximum pages to show in dropdown for large datasets

# ============================================================================
# Gemini Model Configuration
# ============================================================================
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_MAX_TOKENS = 1000000  # 1M token context window
MAX_RETRIES = 3
RETRY_DELAY = 2.0

# Gemini optimization constants
GEMINI_MAX_CONTEXT_TOKENS = 800000  # Stay under 1M limit with buffer
SIMILARITY_THRESHOLD = 0.7  # Jaccard similarity for deduplication

# ============================================================================
# Token Cost Configuration
# ============================================================================
TOKEN_COSTS = {
    'gemini-1.5-pro': {'input': 0.00125, 'output': 0.00375},  # Per 1K tokens
    'gemini-1.5-flash': {'input': 0.000075, 'output': 0.0003},
    'gemini-2.5-flash-lite': {'input': 0.000075, 'output': 0.0003},  # Assumed same as 1.5-flash
    'gpt-4o': {'input': 0.005, 'output': 0.015},
    'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
    'claude-3-haiku': {'input': 0.00025, 'output': 0.00125},
    'claude-3-sonnet': {'input': 0.003, 'output': 0.015}
}

# ============================================================================
# Chat Configuration
# ============================================================================
# Default prompt for chat mode (concise responses)
CHAT_DEFAULT_PROMPT_INSTRUCTION = """
Your responses should be concise and direct (2-3 sentences by default).
Only provide detailed explanations when the user specifically uses @longanswer.
Focus on answering the exact question asked without unnecessary elaboration.
"""

# ============================================================================
# Streamlit Page Configuration
# ============================================================================
STREAMLIT_CONFIG = {
    'page_title': "Simple SQL RAG with Gemini",
    'page_icon': "🔥",
    'layout': "wide"
}

# ============================================================================
# Logging Configuration
# ============================================================================
LOG_LEVEL = "INFO"

# ============================================================================
# UI Configuration
# ============================================================================
# Colors and styling constants
PRIMARY_COLOR = "#0066cc"
BACKGROUND_COLOR = "#ffffff"
SECONDARY_BACKGROUND_COLOR = "#f0f2f6"
TEXT_COLOR = "#262730"

# ============================================================================
# Search Configuration
# ============================================================================
DEFAULT_K = 4  # Default number of documents to retrieve
DEFAULT_HYBRID_SEARCH = False
DEFAULT_QUERY_REWRITING = False
DEFAULT_GEMINI_MODE = True

# ============================================================================
# Feature Flags
# ============================================================================
# These control which optional features are enabled
ENABLE_SCHEMA_MANAGER = True
ENABLE_HYBRID_SEARCH = True
ENABLE_QUERY_REWRITING = True
ENABLE_GRAPHVIZ = True

# ============================================================================
# Cache Configuration
# ============================================================================
# Time to live for Streamlit cache (in seconds)
CACHE_TTL = 3600  # 1 hour

# ============================================================================
# Error Messages
# ============================================================================
ERROR_MESSAGES = {
    'vector_store_not_found': "❌ Vector store not found at: {path}",
    'vector_store_load_error': "❌ Error loading vector store: {error}",
    'csv_not_found': "❌ CSV file not found: {path}",
    'no_data_found': "❌ No data found in the selected file",
    'gemini_connection_failed': "❌ Failed to connect to Gemini. Please check your configuration.",
    'schema_manager_unavailable': "⚠️ Schema manager not available - schema injection disabled"
}

# ============================================================================
# Info Messages
# ============================================================================
INFO_MESSAGES = {
    'first_run_instruction': "💡 First run: python standalone_embedding_generator.py --csv 'your_data.csv'",
    'vector_store_loaded': "✅ Loaded vector store from {path}",
    'schema_manager_loaded': "✅ Schema manager loaded successfully",
    'hybrid_search_initialized': "✅ Hybrid retriever initialized successfully"
}
