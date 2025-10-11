#!/usr/bin/env python3
"""
Common utility functions for SQL RAG Streamlit application.
Originally extracted from app_simple_gemini.py, now properly organized in utils package.
"""

import json
import math
import pandas as pd
from typing import Any, Dict, List

# Import from config with absolute import (no relative imports)
from config import GEMINI_MAX_TOKENS, QUERIES_PER_PAGE


def estimate_token_count(text: str) -> int:
    """Rough estimation of token count (4 chars ≈ 1 token)."""
    return len(text) // 4


def calculate_context_utilization(docs: list, query: str) -> dict:
    """Calculate context utilization for Gemini's 1M token window."""
    
    # Estimate tokens
    query_tokens = estimate_token_count(query)
    context_tokens = sum(estimate_token_count(doc.page_content) for doc in docs)
    total_input_tokens = query_tokens + context_tokens
    
    # Calculate utilization
    utilization_percent = (total_input_tokens / GEMINI_MAX_TOKENS) * 100
    
    return {
        'query_tokens': query_tokens,
        'context_tokens': context_tokens,
        'total_input_tokens': total_input_tokens,
        'utilization_percent': min(utilization_percent, 100),  # Cap at 100%
        'chunks_used': len(docs),
        'avg_tokens_per_chunk': context_tokens / len(docs) if docs else 0
    }


def safe_get_value(row, column: str, default: str = '') -> str:
    """Safely get value from dataframe row, handling missing/empty values"""
    try:
        value = row.get(column, default)
        if pd.isna(value) or value is None:
            return default
        return str(value).strip()
    except:
        return default


def calculate_pagination(total_queries: int, page_size: int = QUERIES_PER_PAGE) -> Dict[str, Any]:
    """Calculate pagination parameters for query display"""
    if total_queries <= 0:
        return {
            'total_pages': 0,
            'page_size': page_size,
            'has_multiple_pages': False,
            'total_queries': 0
        }
    
    total_pages = math.ceil(total_queries / page_size)
    return {
        'total_pages': total_pages,
        'page_size': page_size,
        'has_multiple_pages': total_pages > 1,
        'total_queries': total_queries
    }


def get_page_slice(df: pd.DataFrame, page_num: int, page_size: int = QUERIES_PER_PAGE) -> pd.DataFrame:
    """Get DataFrame slice for specific page"""
    if df.empty or page_num < 1:
        return pd.DataFrame()
    
    start_idx = (page_num - 1) * page_size
    end_idx = start_idx + page_size
    
    # Ensure we don't go beyond the dataframe
    if start_idx >= len(df):
        return pd.DataFrame()
    
    return df.iloc[start_idx:end_idx]


def get_page_info(page_num: int, total_queries: int, page_size: int = QUERIES_PER_PAGE) -> Dict[str, int]:
    """Get information about current page range"""
    start_query = (page_num - 1) * page_size + 1
    end_query = min(page_num * page_size, total_queries)
    
    return {
        'start_query': start_query,
        'end_query': end_query,
        'queries_on_page': end_query - start_query + 1
    }


def get_available_indices(faiss_indices_dir) -> List[str]:
    """Get list of available vector store indices"""
    if not faiss_indices_dir.exists():
        return []
    
    indices = []
    for path in faiss_indices_dir.iterdir():
        if path.is_dir() and path.name.startswith("index_"):
            indices.append(path.name)
    
    return sorted(indices)


def format_cost(cost: float) -> str:
    """Format cost in a readable way"""
    if cost < 0.001:
        return f"${cost * 1000:.3f}m"  # Show in milli-dollars for very small amounts
    elif cost < 1:
        return f"${cost:.4f}"
    else:
        return f"${cost:.2f}"


def calculate_token_cost(prompt_tokens: int, completion_tokens: int, model: str, token_costs: dict) -> float:
    """Calculate cost based on token usage and model pricing"""
    if model not in token_costs:
        return 0.0
    
    costs = token_costs[model]
    prompt_cost = (prompt_tokens / 1000) * costs['input']
    completion_cost = (completion_tokens / 1000) * costs['output']
    
    return prompt_cost + completion_cost


def validate_query_input(query: str) -> tuple[bool, str]:
    """Validate user query input"""
    if not query or not query.strip():
        return False, "Please enter a question"
    
    if len(query.strip()) < 3:
        return False, "Question is too short"
    
    if len(query) > 1000:
        return False, "Question is too long (max 1000 characters)"
    
    return True, ""


def clean_agent_indicator(text: str) -> str:
    """Remove agent indicators from text for clean display"""
    # Remove common agent indicators
    patterns = ['@explain', '@create', '@longanswer']
    cleaned = text
    for pattern in patterns:
        cleaned = cleaned.replace(pattern, '').strip()
    
    # Clean up multiple spaces
    cleaned = ' '.join(cleaned.split())
    return cleaned


def parse_json_safely(json_str: str, default=None):
    """Safely parse JSON string, returning default on error"""
    try:
        if pd.isna(json_str) or json_str == '' or json_str is None:
            return default if default is not None else []
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


def format_number_with_commas(number: int) -> str:
    """Format number with commas for readability"""
    return f"{number:,}"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length with suffix"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def extract_agent_type(user_input: str) -> tuple[str, str]:
    """Extract agent type from user input and return cleaned input"""
    user_input = user_input.strip()
    
    # Check for agent indicators
    if user_input.lower().startswith('@explain'):
        return 'explain', user_input[8:].strip()
    elif user_input.lower().startswith('@create'):
        return 'create', user_input[7:].strip()
    elif '@longanswer' in user_input.lower():
        return 'longanswer', user_input.replace('@longanswer', '').strip()
    
    return None, user_input


def is_empty_or_whitespace(value) -> bool:
    """Check if value is empty, None, or just whitespace"""
    if value is None:
        return True
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    return False