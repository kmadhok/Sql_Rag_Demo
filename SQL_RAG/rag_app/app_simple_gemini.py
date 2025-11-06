#!/usr/bin/env python3
"""
Gemini-Optimized Simple Retail-SQL RAG Streamlit App

A Windows-compatible Streamlit interface optimized for Gemini's 1M context window
that directly loads pre-built vector stores created by standalone_embedding_generator.py

Usage:
    1. First run: python standalone_embedding_generator.py --csv "your_data.csv"
    2. Then run: streamlit run app_simple_gemini.py

Features:
- Direct vector store loading from faiss_indices/ directory
- Gemini 1M context window optimization with 18.5x better utilization
- Smart deduplication and content prioritization
- Real-time context utilization monitoring
- Question/answer interface with enhanced source attribution
- Windows compatible with no complex processors
"""

import streamlit as st
import os
import pandas as pd
import time
import logging
import re
import json
import os
import math
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
from collections import defaultdict


def _resolve_env_path(key: str, default: Path) -> Path:
    """Helper to resolve paths from environment variables."""
    value = os.getenv(key)
    if value:
        return Path(value).expanduser()
    return default


def _env_vector_store(default: str) -> str:
    """Resolve vector store name from environment variables."""
    return (
        os.getenv("DEFAULT_VECTOR_STORE")
        or os.getenv("VECTOR_STORE_NAME")
        or default
    )

# Load environment variables from .env if present (for GEMINI_API_KEY, etc.)
try:
    from dotenv import load_dotenv, find_dotenv
    _dotenv_path = find_dotenv(usecwd=True)
    if _dotenv_path:
        load_dotenv(_dotenv_path, override=False)
        logging.getLogger(__name__).info(f"Loaded environment from {_dotenv_path}")
except Exception as _e:
    logging.getLogger(__name__).debug(f"dotenv not loaded: {_e}")

# LangChain imports
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Optional graph support for join visualization
try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False

# Import our enhanced RAG function and hybrid search components
from utils.embedding_provider import get_provider_info
from prompt_templates import get_chat_prompt_template

# Import conversation management
try:
    from core.conversation_manager import get_conversation_manager
    CONVERSATION_MANAGER_AVAILABLE = True
except ImportError:
    CONVERSATION_MANAGER_AVAILABLE = False

# Configure logging (idempotent)
if not logging.getLogger(__name__).handlers:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import utility functions
from utils.app_utils import (
    estimate_token_count,
    calculate_context_utilization,
    safe_get_value,
    get_user_session_id,
    calculate_conversation_tokens,
    _fast_extract_tables,
    detect_agent_type,
    detect_chat_agent_type,
    get_agent_indicator,
    get_chat_agent_indicator,
    calculate_pagination,
    get_page_slice,
    get_page_info,
    auto_save_conversation
)

from services.query_search_service import (
    QuerySearchSettings,
    run_query_search
)
from services.sql_execution_service import (
    SQLExecutionSettings,
    initialize_executor,
    run_sql_execution,
    validate_sql_safety
)

# Import data loading functions
from data.app_data_loader import (
    load_vector_store,
    load_csv_data,
    load_lookml_safe_join_map,
    load_schema_manager,
    get_available_indices,
    load_cached_analytics,
    load_cached_graph_files
)

# Import UI page functions
from ui.pages import (
    create_query_catalog_page,
    create_data_page,
    create_chat_page,
    create_introduction_page
)

# Import necessary components for chat-specific RAG function
from gemini_client import GeminiClient

# Import schema manager for smart schema injection
try:
    from schema_manager import SchemaManager, create_schema_manager
    SCHEMA_MANAGER_AVAILABLE = True
except ImportError:
    SCHEMA_MANAGER_AVAILABLE = False
    # Logger may not be configured yet at import time; fall back to root logger
    logging.warning("Schema manager not available - schema injection disabled")

# Import hybrid search components
try:
    from hybrid_retriever import SearchWeights
    HYBRID_SEARCH_AVAILABLE = True
except ImportError:
    HYBRID_SEARCH_AVAILABLE = False

# Import SQL validation components
try:
    from core.sql_validator import ValidationLevel
    SQL_VALIDATION_AVAILABLE = True
except ImportError:
    ValidationLevel = None  # type: ignore
    SQL_VALIDATION_AVAILABLE = False

# Import BigQuery execution components
try:
    from core.bigquery_executor import BigQueryExecutor, QueryResult, format_bytes, format_execution_time
    BIGQUERY_EXECUTION_AVAILABLE = True
except ImportError:
    BIGQUERY_EXECUTION_AVAILABLE = False

# # Configure logging (idempotent)
# if not logging.getLogger(__name__).handlers:
#     logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# Configuration - Enhanced with backwards compatibility
try:
    from config.app_config import app_config
    # Use modern configuration if available
    FAISS_INDICES_DIR = app_config.FAISS_INDICES_DIR
    DEFAULT_VECTOR_STORE = app_config.DEFAULT_VECTOR_STORE
    CSV_PATH = app_config.CSV_PATH
    CATALOG_ANALYTICS_DIR = app_config.CATALOG_ANALYTICS_DIR
    SCHEMA_CSV_PATH = app_config.SCHEMA_CSV_PATH
    LOOKML_SAFE_JOIN_MAP_PATH = FAISS_INDICES_DIR / "lookml_safe_join_map.json"
    _secondary_map_env = os.getenv("LOOKML_SAFE_JOIN_MAP_PATH")
    SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH = (
        Path(_secondary_map_env).expanduser()
        if _secondary_map_env
        else Path(__file__).parent / "lookml_safe_join_map.json"
    )
    LOOKML_DIR = Path(os.getenv("LOOKML_DIR", Path(__file__).parent / "lookml_data")).expanduser()
    
    # Pagination config
    QUERIES_PER_PAGE = app_config.QUERIES_PER_PAGE
    MAX_PAGES_TO_SHOW = app_config.MAX_PAGES_TO_SHOW
    
except ImportError:
    # Fallback to original configuration
    logger.info("Using legacy configuration (app_config not available)")
    _BASE_DIR = Path(__file__).parent
    FAISS_INDICES_DIR = _resolve_env_path("FAISS_INDICES_DIR", _BASE_DIR / "faiss_indices")
    DEFAULT_VECTOR_STORE = _env_vector_store("index_sample_queries_with_metadata_recovered")
    CSV_PATH = _resolve_env_path("CSV_PATH", _BASE_DIR / "sample_queries_with_metadata.csv")
    CATALOG_ANALYTICS_DIR = _resolve_env_path("CATALOG_ANALYTICS_DIR", _BASE_DIR / "catalog_analytics")
    SCHEMA_CSV_PATH = _resolve_env_path("SCHEMA_CSV_PATH", _BASE_DIR / "data_new/thelook_ecommerce_schema.csv")
    LOOKML_SAFE_JOIN_MAP_PATH = FAISS_INDICES_DIR / "lookml_safe_join_map.json"
    SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH = _resolve_env_path("LOOKML_SAFE_JOIN_MAP_PATH", _BASE_DIR / "lookml_safe_join_map.json")
    LOOKML_DIR = _resolve_env_path("LOOKML_DIR", _BASE_DIR / "lookml_data")
    
    # Legacy pagination config
    QUERIES_PER_PAGE = 15
    MAX_PAGES_TO_SHOW = 10

# Pagination Configuration - Unified (removes duplication)
# Note: QUERIES_PER_PAGE and MAX_PAGES_TO_SHOW already defined above

# Streamlit page config
st.set_page_config(
    page_title="Ask Data Questions in Plain English | SQL RAG",
    page_icon="⚡",
    layout="wide"
)













def display_query_card(row, index: int):
    """Display a single query card using pre-parsed data for optimal performance"""
    query = safe_get_value(row, 'query')
    description = safe_get_value(row, 'description')
    
    # Use pre-parsed columns (available from optimized_queries.parquet/csv)
    if 'tables_parsed' in row and isinstance(row['tables_parsed'], list):
        tables_list = row['tables_parsed']
    else:
        # Fallback for original CSV data
        tables_raw = safe_get_value(row, 'tables')
        tables_list = []  # Skip parsing - recommend using pre-computed cache
        if tables_raw:
            st.caption("⚠️ Table parsing skipped - use pre-computed cache for better performance")
    
    if 'joins_parsed' in row and isinstance(row['joins_parsed'], list):
        joins_list = row['joins_parsed']
    else:
        # Fallback for original CSV data
        joins_raw = safe_get_value(row, 'joins')
        joins_list = []  # Skip parsing - recommend using pre-computed cache
        if joins_raw:
            st.caption("⚠️ Join parsing skipped - use pre-computed cache for better performance")
    
    # Create title based on available data
    if description:
        title = f"Query {index + 1}: {description[:60]}{'...' if len(description) > 60 else ''}"
    else:
        title = f"Query {index + 1}: {query[:40]}{'...' if len(query) > 40 else ''}"
    
    # Add join count to title if multiple joins
    if len(joins_list) > 1:
        title += f" • {len(joins_list)} joins"
    elif len(joins_list) == 1:
        title += " • 1 join"
    
    with st.expander(title):
        # Always show the SQL query
        st.markdown("**SQL Query:**")
        st.code(query, language="sql")
        
        # Only show sections with actual data
        metadata_shown = False
        
        if description:
            st.markdown(f"**Description:** {description}")
            metadata_shown = True
        
        if tables_list:
            if len(tables_list) == 1:
                st.markdown(f"**Table:** {tables_list[0]}")
            else:
                st.markdown(f"**Tables:** {', '.join(tables_list)}")
            metadata_shown = True
        
        if joins_list:
            if len(joins_list) == 1:
                st.markdown("**Join Information:**")
                display_single_join(joins_list[0])
            else:
                st.markdown(f"**Join Information ({len(joins_list)} joins):**")
                for i, join_info in enumerate(joins_list, 1):
                    st.markdown(f"**Join {i}:**")
                    display_single_join(join_info, indent=True)
                    if i < len(joins_list):  # Add separator between joins
                        st.markdown("---")
            
            metadata_shown = True
        
        if not metadata_shown and not (description or tables_list or joins_list):
            st.caption("_No additional metadata available_")

def display_single_join(join_info: Dict[str, Any], indent: bool = False):
    """Display a single join with structured information"""
    prefix = "  " if indent else ""
    
    if join_info['format'] == 'json':
        # Rich display for JSON format
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"{prefix}- **Join Type:** {join_info['join_type']}")
            st.markdown(f"{prefix}- **Left Table:** {join_info['left_table']}")
            st.markdown(f"{prefix}- **Right Table:** {join_info['right_table']}")
        
        with col2:
            if join_info['left_column'] and join_info['right_column']:
                st.markdown(f"{prefix}- **Left Column:** {join_info['left_column']}")
                st.markdown(f"{prefix}- **Right Column:** {join_info['right_column']}")
        
        if join_info['transformation']:
            st.markdown(f"{prefix}- **Transformation:** `{join_info['transformation']}`")
        else:
            st.markdown(f"{prefix}- **Condition:** `{join_info['condition']}`")
    else:
        # Simple display for string format
        st.markdown(f"{prefix}- **Condition:** `{join_info['condition']}`")
        if join_info['left_table'] != 'unknown':
            st.markdown(f"{prefix}- **Tables:** {join_info['left_table']} ↔ {join_info['right_table']}")

# REMOVED: analyze_joins() - now loading pre-computed analytics from join_analysis.json

def display_join_analysis(join_analysis: Dict):
    """Display enhanced join analysis with multi-join array support"""
    st.subheader("📊 Data Statistics")
    
    # Display main statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Queries", join_analysis['total_queries'])
    
    with col2:
        st.metric("With Descriptions", join_analysis['queries_with_descriptions'])
    
    with col3:
        st.metric("With Tables", join_analysis['queries_with_tables'])
    
    with col4:
        st.metric("With Joins", join_analysis['queries_with_joins'])
    
    # Join complexity statistics
    if join_analysis['total_individual_joins'] > 0:
        st.subheader("🔗 Join Complexity")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Individual Joins", join_analysis['total_individual_joins'])
        
        with col2:
            avg_joins = join_analysis['total_individual_joins'] / max(join_analysis['queries_with_joins'], 1)
            st.metric("Avg Joins per Query", f"{avg_joins:.1f}")
        
        with col3:
            st.metric("Max Joins in Single Query", join_analysis['max_joins_per_query'])
        
        # Join count distribution
        if join_analysis['join_count_distribution']:
            st.subheader("📊 Join Count Distribution")
            distribution_data = []
            for join_count, query_count in sorted(join_analysis['join_count_distribution'].items()):
                if join_count == 0:
                    label = "No joins"
                elif join_count == 1:
                    label = "1 join"
                else:
                    label = f"{join_count} joins"
                distribution_data.append({'Join Count': label, 'Queries': query_count})
            
            distribution_df = pd.DataFrame(distribution_data)
            st.dataframe(distribution_df, use_container_width=True, hide_index=True)
    
    # Format statistics (if there are joins)
    if join_analysis['total_individual_joins'] > 0:
        st.subheader("📋 Format Statistics")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("JSON Format Joins", join_analysis['json_format_count'])
        
        with col2:
            st.metric("String Format Joins", join_analysis['string_format_count'])
    
    # Join type distribution
    if join_analysis['join_types']:
        st.subheader("🔀 Join Types")
        join_types_df = pd.DataFrame(
            list(join_analysis['join_types'].items()),
            columns=['Join Type', 'Count']
        ).sort_values('Count', ascending=False)
        
        st.dataframe(join_types_df, use_container_width=True, hide_index=True)
    
    # Table usage frequency
    if join_analysis['table_usage']:
        st.subheader("📋 Table Usage Frequency")
        table_usage = dict(join_analysis['table_usage'])
        usage_df = pd.DataFrame(
            list(table_usage.items()), 
            columns=['Table', 'Usage Count']
        ).sort_values('Usage Count', ascending=False)
        
        st.dataframe(usage_df, use_container_width=True, hide_index=True)
    
    # Join relationships
    if join_analysis['relationships']:
        st.subheader("🔗 Join Relationships")
        
        relationships_df = pd.DataFrame(join_analysis['relationships'])
        if not relationships_df.empty:
            # Display different columns based on available data
            display_columns = ['left_table', 'right_table', 'join_type']
            
            # Add condition or transformation
            if 'transformation' in relationships_df.columns:
                # Show transformation for JSON format, condition for others
                relationships_df['join_detail'] = relationships_df.apply(
                    lambda row: row.get('transformation', '') or row.get('condition', ''), 
                    axis=1
                )
                display_columns.append('join_detail')
            else:
                display_columns.append('condition')
            
            # Show format information
            if 'format' in relationships_df.columns:
                display_columns.append('format')
            
            # Filter to existing columns
            available_columns = [col for col in display_columns if col in relationships_df.columns]
            
            st.dataframe(
                relationships_df[available_columns], 
                use_container_width=True,
                hide_index=True
            )
        
        # REMOVED: Graph visualization moved to static files in create_query_catalog_page()
        # This eliminates expensive graph generation during runtime
    else:
        st.info("No join relationships found in the data")






    
    st.divider()
    # Download schema CSV
    try:
        with open(SCHEMA_CSV_PATH, 'rb') as f:
            csv_bytes = f.read()
        st.download_button("⬇️ Download Schema CSV", data=csv_bytes, file_name=SCHEMA_CSV_PATH.name, mime="text/csv")
    except Exception:
        pass

def find_original_queries_for_sources(sources: List[Document], csv_data: pd.DataFrame) -> List[pd.Series]:
    """
    Map vector store sources back to original CSV query rows
    
    Args:
        sources: List of Document objects from vector store search
        csv_data: DataFrame containing original queries
        
    Returns:
        List of unique CSV rows that correspond to the sources
    """
    if not sources or csv_data.empty:
        return []
    
    matched_queries = []
    seen_queries = set()  # Track unique queries to avoid duplicates
    
    for doc in sources:
        # Try to match based on content similarity
        chunk_content = doc.page_content.strip().lower()
        
        # Look for the best matching query in CSV data
        best_match = None
        best_similarity = 0
        
        for idx, row in csv_data.iterrows():
            query_content = safe_get_value(row, 'query').strip().lower()
            
            # Skip empty queries
            if not query_content:
                continue
            
            # Calculate similarity (simple approach - substring matching)
            # More sophisticated approaches could use fuzzy matching or embeddings
            if chunk_content in query_content or query_content in chunk_content:
                similarity = min(len(chunk_content), len(query_content)) / max(len(chunk_content), len(query_content))
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = row
            
            # Also try exact query matching if chunk contains the full query
            if query_content in chunk_content and len(query_content) > 50:  # Avoid matching very short queries
                best_match = row
                best_similarity = 1.0
                break
        
        # Add the best match if it's good enough and not already seen
        if best_match is not None and best_similarity > 0.3:  # Minimum similarity threshold
            query_key = safe_get_value(best_match, 'query')[:100]  # Use first 100 chars as unique key
            
            if query_key not in seen_queries:
                matched_queries.append(best_match)
                seen_queries.add(query_key)
    
    # Sort by relevance (maintain original source order for first occurrence)
    return matched_queries

def display_session_stats():
    """Display session token usage statistics"""
    if 'token_usage' not in st.session_state:
        st.session_state.token_usage = []
    
    total_tokens = sum(usage.get('total_tokens', 0) for usage in st.session_state.token_usage)
    query_count = len(st.session_state.token_usage)
    
    if query_count > 0:
        st.markdown(f"""
        <div style="background-color: #262730; color: white; padding: 15px; border-radius: 10px; margin: 10px 0;">
            <strong>📊 Session Stats:</strong> 
            {total_tokens:,} tokens | {query_count} queries | 🔥 Gemini-Optimized | 🤖 Google Gemini 2.5 Flash
        </div>
        """, unsafe_allow_html=True)


        return "💬 Concise Chat"


def handle_schema_query(question: str, lookml_safe_join_map: Optional[Dict[str, Any]]) -> str:
    """
    Handle @schema queries for direct LookML exploration
    
    Args:
        question: User's schema question
        lookml_safe_join_map: LookML safe-join map data
        
    Returns:
        Direct response about schema/joins without using Gemini
    """
    if not lookml_safe_join_map:
        return "❌ LookML safe-join map not available. Please ensure LookML files were processed during embedding generation."
    
    question_lower = question.lower()
    explores = lookml_safe_join_map.get('explores', {})
    join_graph = lookml_safe_join_map.get('join_graph', {})
    metadata = lookml_safe_join_map.get('metadata', {})
    
    # Handle different types of schema queries
    if not question.strip():
        # No specific query - show overview
        return f"""🗂️ **LookML Schema Overview**

📊 **Project**: {lookml_safe_join_map.get('project', 'Unknown')}
📈 **Available Explores**: {metadata.get('total_explores', 0)}
🔗 **Total Joins**: {metadata.get('total_joins', 0)}

**Explores Available:**
{chr(10).join([f"• **{explore_name}**: {explore_data.get('label', explore_name)} - {explore_data.get('description', 'No description')}" for explore_name, explore_data in explores.items()])}

💡 **Try asking**: "@schema how do I join users with orders" or "@schema show me ecommerce explores"
"""
    
    elif any(word in question_lower for word in ['join', 'relationship', 'connect']):
        # Join-related query
        if 'users' in question_lower and 'orders' in question_lower:
            users_explore = explores.get('users', {})
            if users_explore:
                orders_join = users_explore.get('joins', {}).get('orders', {})
                if orders_join:
                    return f"""🔗 **Users → Orders Join**

**SQL Join Condition**: `{orders_join.get('sql_on', 'Not available')}`
**Relationship**: {orders_join.get('relationship', 'Unknown')}
**Join Type**: {orders_join.get('join_type', 'Unknown')}

**Explore Context**: {users_explore.get('label', 'Users')}
**Path**: {users_explore.get('description', 'User → Orders → Order Items → Products')}
"""
                    
        # Generic join query - show all possible joins
        result = "🔗 **Available Join Relationships**\n\n"
        for explore_name, tables in join_graph.items():
            if tables:
                result += f"**{explore_name}** can join with: {', '.join(tables)}\n"
        return result
        
    elif 'explore' in question_lower:
        # Explore-related query
        result = "📊 **Available Explores**\n\n"
        for explore_name, explore_data in explores.items():
            label = explore_data.get('label', explore_name)
            description = explore_data.get('description', 'No description')
            base_table = explore_data.get('base_table', 'Unknown')
            join_count = len(explore_data.get('joins', {}))
            
            result += f"**{label}** (`{explore_name}`)\n"
            result += f"  • Base Table: {base_table}\n"
            result += f"  • Available Joins: {join_count}\n"
            result += f"  • Description: {description}\n\n"
        return result
        
    else:
        # Search for specific table mentions
        mentioned_tables = [table for table in join_graph.keys() if table in question_lower]
        if mentioned_tables:
            result = f"🗂️ **Schema Information for: {', '.join(mentioned_tables)}**\n\n"
            for table in mentioned_tables:
                if table in explores:
                    explore_data = explores[table]
                    result += f"**{table}**\n"
                    result += f"  • Label: {explore_data.get('label', table)}\n"
                    result += f"  • Base Table: {explore_data.get('base_table', 'Unknown')}\n"
                    result += f"  • Can join with: {', '.join(join_graph.get(table, []))}\n\n"
            return result
        else:
            return f"""❓ **Schema Query Not Recognized**

I can help with:
• **General overview**: "@schema" (no question)
• **Join relationships**: "@schema how to join users with orders"
• **Explore listing**: "@schema show explores"
• **Table information**: "@schema tell me about users table"

Available tables: {', '.join(join_graph.keys())}
"""


def answer_question_chat_mode(
    question: str, 
    vector_store, 
    k: int = 20,
    schema_manager=None,
    conversation_context: str = "",
    agent_type: Optional[str] = None,
    user_context: str = "",
    excluded_tables: Optional[List[str]] = None
) -> Optional[Tuple[str, List[Document], Dict[str, Any]]]:
    """
    Chat-specific RAG function with concise default responses
    
    Args:
        question: User question
        vector_store: Pre-loaded FAISS vector store
        k: Number of similar documents to retrieve
        schema_manager: Optional SchemaManager for smart schema injection
        conversation_context: Previous conversation history for context continuity
        agent_type: Chat agent specialization type ("explain", "create", "longanswer", or None for concise)
        
    Returns:
        Tuple of (answer, source_documents, token_usage) or None if failed
    """
    
    try:
        # Step 1: Retrieve relevant documents using vector search with timeout + keyword fallback
        retrieval_start = time.time()
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
        embedding_timeout = float(os.getenv('EMBEDDING_TIMEOUT_SECONDS', '15'))
        
        def _do_vector_search():
            return vector_store.similarity_search(question, k=k)
        
        docs = []
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(_do_vector_search)
                docs = fut.result(timeout=embedding_timeout)
        except FuturesTimeout:
            logger.warning(f"Chat vector search timed out after {embedding_timeout}s. Falling back to keyword-only search if available.")
            if HYBRID_SEARCH_AVAILABLE:
                try:
                    from hybrid_retriever import HybridRetriever
                    # Build a one-off hybrid retriever for fallback
                    # Extract documents from vector store docstore
                    documents = []
                    docstore = vector_store.docstore
                    if hasattr(docstore, '_dict'):
                        for _id, d in docstore._dict.items():
                            if isinstance(d, Document):
                                documents.append(d)
                    hr = HybridRetriever(vector_store, documents)
                    docs = hr.search(question, k=k, method='keyword')
                    logger.info(f"Chat keyword fallback: {len(docs)} documents retrieved")
                except Exception as e:
                    logger.warning(f"Chat keyword fallback failed: {e}")
                    docs = []
        retrieval_time = time.time() - retrieval_start
        
        # Step 2: Build context from retrieved documents
        # Use simple context building for chat (keep it fast and focused)
        context = f"Question: {question}\n\nRelevant SQL examples:\n\n"
        for i, doc in enumerate(docs, 1):
            context += f"Example {i}:\n{doc.page_content}\n\n"
        
        # Step 3: Handle schema injection if available
        relevant_schema = ""
        schema_info = {}
        
        if schema_manager:
            try:
                # Fast regex extractor to avoid expensive LLM calls per document
                # Use the utility function for table extraction
                import re as _re
                def _fast_extract_tables(text: str) -> List[str]:
                    if not text or not isinstance(text, str):
                        return []
                    tables = set()
                    text_lower = text.lower()
                    patterns = [
                        r'\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                        r'\b(?:inner\s+|left\s+|right\s+|full\s+|cross\s+)?join\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                        r'\bupdate\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                        r'\binsert\s+into\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                    ]
                    for pat in patterns:
                        for match in _re.findall(pat, text_lower):
                            # Simple table normalization for this context
                            table_name = match.split('.')[-1]  # Remove schema prefix if any
                            if table_name and table_name not in {'SELECT', 'WHERE', 'ORDER'}:
                                tables.add(table_name)
                    return list(tables)

                # Derive relevant tables from a limited number of docs + question
                doc_limit = int(os.getenv('CHAT_SCHEMA_DOC_LIMIT', '25'))
                derived_tables = []
                for d in docs[:doc_limit]:
                    derived_tables += _fast_extract_tables(getattr(d, 'page_content', ''))
                derived_tables += _fast_extract_tables(question)

                # Apply exclusions if provided
                excluded_set = {schema_manager._normalize_table_name(t) for t in (excluded_tables or [])}
                filtered_tables = [t for t in derived_tables if schema_manager._normalize_table_name(t) not in excluded_set]

                # Build relevant schema
                schema_text = schema_manager.get_relevant_schema(filtered_tables, max_tables=10)
                if schema_text:
                    # Append exclusion directive
                    if excluded_set:
                        excl_list = ", ".join(sorted(excluded_set))
                        schema_text += f"\n\nEXCLUDED TABLES: {excl_list}\nInstruction: Do not reference excluded tables in the SQL."
                    relevant_schema = schema_text
                    schema_info = {
                        'enabled': True,
                        'relevant_tables': len(filtered_tables),
                        'schema_tokens': estimate_token_count(relevant_schema),
                        'total_schema_tables': schema_manager.table_count,
                        'schema_coverage': f"{len(filtered_tables)}/{schema_manager.table_count}",
                        'schema_available': True
                    }
                else:
                    schema_info = {'enabled': True, 'schema_available': False}
            except Exception as e:
                logger.warning(f"Schema injection failed: {e}")
                schema_info = {'enabled': True, 'schema_available': False, 'error': str(e)}
        else:
            schema_info = {'enabled': False}
        
        # Step 4: Generate answer using LLM with chat-specific prompts
        logger.info(f"Generating chat response...")
        
        # Build prompt sections
        schema_section = f"\nDatabase Schema (relevant tables):\n{relevant_schema}\n" if relevant_schema else ""
        conversation_section = f"\nPrevious conversation:\n{conversation_context}\n" if conversation_context.strip() else ""
        
        # If we have an available schema manager, add BigQuery FQN mapping to schema section
        if schema_manager and relevant_schema:
            try:
                # Reuse derived tables for FQN map to avoid duplicate extraction
                tables_for_map = list(dict.fromkeys(derived_tables))
                # Respect exclusions in FQN map
                excluded_set = {schema_manager._normalize_table_name(t) for t in (excluded_tables or [])}
                tables_for_map = [t for t in tables_for_map if schema_manager._normalize_table_name(t) not in excluded_set]
                fqn_map = schema_manager.get_fqn_map(tables_for_map)
            except Exception:
                fqn_map = {}
            if fqn_map:
                lines = ["\nBIGQUERY FULLY QUALIFIED TABLES (use in FROM/JOIN):"]
                for t, fqn in fqn_map.items():
                    lines.append(f"  - {t} -> `{fqn}`")
                lines.append("\nInstruction: Always use fully-qualified names (project.dataset.table). Aliases are fine after qualification.")
                relevant_schema = relevant_schema + "\n" + "\n".join(lines)

        # Rebuild schema section after appending FQN block
        schema_section = f"\nDatabase Schema (relevant tables):\n{relevant_schema}\n" if relevant_schema else ""

        # Add user-provided context into the prompt context
        if user_context and user_context.strip():
            context = f"User Context (high priority):\n{user_context.strip()}\n\n" + context

        # Use chat-specific prompt template
        prompt = get_chat_prompt_template(
            agent_type=agent_type,
            question=question,
            schema_section=schema_section,
            conversation_section=conversation_section,
            context=context
        )
        
        # Initialize LLM and generate response
        # Use registry-defined chat model (default: gemini-2.5-flash-lite)
        try:
            from llm_registry import get_llm_registry
            llm = get_llm_registry().get_chat()
        except Exception:
            llm = GeminiClient(model=os.getenv("LLM_CHAT_MODEL", "gemini-2.5-flash-lite"))
        
        generation_start = time.time()
        answer = llm.invoke(prompt)
        generation_time = time.time() - generation_start
        
        # Calculate token usage
        prompt_tokens = estimate_token_count(prompt)
        completion_tokens = estimate_token_count(answer)
        total_tokens = prompt_tokens + completion_tokens
        
        # Chat-specific token usage tracking
        token_usage = {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'search_method': 'vector',  # Chat uses simple vector search
            'retrieval_time': retrieval_time,
            'generation_time': generation_time,
            'documents_retrieved': len(docs),
            'documents_processed': len(docs),
            'agent_type': agent_type,
            'mode': 'chat',  # Indicator that this is chat mode
            'schema_filtering': schema_info
        }
        
        logger.info(f"Chat response generated successfully in {generation_time:.2f}s")
        return answer, docs, token_usage
        
    except Exception as e:
        logger.error(f"Error in chat mode: {e}", exc_info=True)
        return None




def render_chat_message(msg, is_user=True):
    """Render a single chat message using Streamlit's native chat components"""
    agent_type = msg.get('agent_type')
    content = msg.get('content', '')
    
    # Use Streamlit's native chat message component
    role = "user" if is_user else "assistant"
    
    with st.chat_message(role):
        if not is_user:
            # Show agent indicator for assistant messages
            agent_indicator = get_chat_agent_indicator(agent_type)
            st.caption(f"🤖 {agent_indicator}")
        else:
            # Show agent indicator for user messages if they used a keyword
            if agent_type:
                agent_indicator = get_chat_agent_indicator(agent_type)
                st.caption(f"🎯 {agent_indicator}")
        
        # Display the message content
        st.markdown(content)
        
        # Show sources for assistant messages
        if not is_user and msg.get('sources'):
            with st.expander(f"📚 View {len(msg['sources'])} Source(s)", expanded=False):
                for j, doc in enumerate(msg['sources'], 1):
                    st.markdown(f"**📄 Source {j}:**")
                    st.code(doc.page_content, language="sql")
                    if j < len(msg['sources']):
                        st.divider()



    
    # Show detailed token breakdown at bottom if there are messages
    if st.session_state.chat_messages:
        st.divider()
        
        # Enhanced session stats
        stats = calculate_conversation_tokens(st.session_state.chat_messages)
        
        st.markdown("### 📊 Session Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Conversation Tokens",
                f"{stats['conversation_tokens']:,}",
                "Messages only"
            )
        
        with col2:
            st.metric(
                "Context Tokens", 
                f"{stats['context_tokens']:,}",
                "Retrieved sources"
            )
        
        with col3:
            st.metric(
                "API Response Tokens",
                f"{stats['response_tokens']:,}",
                "Gemini API usage"
            )
        
        with col4:
            remaining = 1000000 - stats['total_tokens']
            st.metric(
                "Remaining Capacity",
                f"{remaining:,}",
                f"{100 - stats['utilization_percent']:.1f}% free"
            )


def display_sql_execution_interface(answer: str):
    """
    Display SQL execution interface when SQL is detected in the answer
    
    Args:
        answer: The generated answer text that may contain SQL
    """
    advanced = st.session_state.get('advanced_mode', False)
    # Debug option (advanced only)
    if advanced:
        debug_mode = st.checkbox("🐛 Debug Mode", help="Show detailed execution logging", key="sql_execution_debug_checkbox")
        st.session_state.debug_mode = debug_mode
    else:
        debug_mode = False
        st.session_state.debug_mode = False
    
    if debug_mode:
        st.write("**Debug Info:**")
        st.write(f"- BigQuery Available: {BIGQUERY_EXECUTION_AVAILABLE}")
        st.write(f"- Session State Keys: {list(st.session_state.keys())}")
        if 'extracted_sql' in st.session_state:
            st.write(f"- SQL in Session State: {bool(st.session_state.extracted_sql)}")
        st.write(f"- SQL Executing: {st.session_state.get('sql_executing', False)}")
        st.write(f"- SQL Execution Completed: {st.session_state.get('sql_execution_completed', False)}")
        st.write(f"- Has Execution Result: {'sql_execution_result' in st.session_state}")
        st.write(f"- Has Execution Error: {'sql_execution_error' in st.session_state}")
        
    if not BIGQUERY_EXECUTION_AVAILABLE:
        st.warning("⚠️ BigQuery execution unavailable - check bigquery_executor.py and dependencies")
        logger.warning("BigQuery execution not available")
        return
    
    # Initialize BigQuery executor
    if 'bigquery_executor' not in st.session_state:
        try:
            if debug_mode:
                st.write("🔧 Initializing BigQuery executor...")
            settings = SQLExecutionSettings()
            st.session_state.bigquery_executor = initialize_executor(settings)
            logger.info(
                "✅ BigQuery executor initialized successfully (project=%s, dataset=%s)",
                st.session_state.bigquery_executor.project_id,
                st.session_state.bigquery_executor.dataset_id
            )
            if debug_mode:
                st.success("✅ BigQuery executor initialized")
        except Exception as e:
            error_msg = f"Failed to initialize BigQuery executor: {e}"
            st.error(f"❌ {error_msg}")
            logger.error(f"❌ {error_msg}")
            return
    
    executor = st.session_state.bigquery_executor
    
    # Check for existing SQL in session state FIRST (persistence priority)
    extracted_sql = None
    
    # Protection: Don't overwrite SQL if execution is in progress
    if st.session_state.get('sql_executing', False):
        if debug_mode:
            st.write("🔒 **SQL execution in progress** - using existing SQL")
        extracted_sql = st.session_state.get('extracted_sql')
    elif 'extracted_sql' in st.session_state and st.session_state.extracted_sql:
        # Use existing SQL from session state
        extracted_sql = st.session_state.extracted_sql
        logger.info("📋 Using SQL from session state (persistent)")
        if debug_mode:
            st.write("📋 **Using SQL from session state** (avoiding re-extraction)")
    else:
        # Extract SQL from answer only if not in session state and not executing
        if debug_mode:
            st.write("🔍 **Extracting SQL from answer text**...")
        extracted_sql = executor.extract_sql_from_text(answer)
        
        if extracted_sql:
            # Store newly extracted SQL in session state for persistence
            st.session_state.extracted_sql = extracted_sql
            logger.info(f"💾 Extracted and stored new SQL in session state: {extracted_sql[:50]}...")
            if debug_mode:
                st.write(f"💾 **Extracted new SQL** ({len(extracted_sql)} chars)")
        else:
            logger.warning("❌ No SQL found in answer text")
            if debug_mode:
                st.write("❌ **No SQL found** in answer text")
    
    if extracted_sql:
        if debug_mode:
            st.write(f"✅ **SQL Available** - {len(extracted_sql)} characters")
        
        st.divider()
        st.subheader("🚀 Execute SQL Query")
        st.caption("Detected SQL query in the response - execute it against BigQuery thelook_ecommerce dataset")
        
        # Display the SQL with syntax highlighting
        st.markdown("**📝 Generated SQL Query:**")
        st.code(extracted_sql, language="sql")
        
        # Safety validation using shared service
        if debug_mode:
            st.write("🔒 **Running safety validation**...")
        is_valid, validation_msg = validate_sql_safety(extracted_sql, executor)
        
        if is_valid:
            st.success("✅ Query passed safety validation")
            if debug_mode and validation_msg:
                st.info(f"Validator message: {validation_msg}")
            logger.info("✅ SQL query passed safety validation")
        else:
            error_msg = f"Safety validation failed: {validation_msg}"
            st.error(f"🚫 {error_msg}")
            logger.warning(f"🚫 {error_msg}")
            if debug_mode and validation_msg:
                st.write(f"🚫 **Validation details:** {validation_msg}")
            return
        
        # Execution form to prevent unwanted reruns (submit button only in form)
        with st.form(key="sql_execution_form"):
            st.markdown("**⚙️ Execution Settings:**")
            if advanced:
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"📊 **Project:** {executor.project_id}")
                    st.info(f"🗃️ **Dataset:** {executor.dataset_id}")
                with col2:
                    st.info(f"🔒 **Max Rows:** {executor.max_rows:,}")
                    st.info(f"⏱️ **Timeout:** {executor.timeout_seconds}s")
                with st.expander("Execution Controls", expanded=False):
                    dry_run = st.checkbox(
                        "🧪 Dry Run (estimate only)",
                        value=st.session_state.get('bq_dry_run', False),
                        help="Estimate bytes processed without returning results"
                    )
                    st.session_state['bq_dry_run'] = dry_run
                    max_bytes_default = int(st.session_state.get('bq_max_bytes_billed', 100_000_000))
                    max_bytes_billed = st.number_input(
                        "💰 Max Bytes Billed",
                        min_value=10_000_000,
                        value=max_bytes_default,
                        step=10_000_000,
                        help="Safety cap on billed bytes"
                    )
                    st.session_state['bq_max_bytes_billed'] = int(max_bytes_billed)
                # Submit button (required inside form)
                st.form_submit_button(
                    "▶️ Execute Query",
                    type="primary",
                    help="Execute the SQL query against BigQuery",
                    on_click=execute_sql_callback
                )
            else:
                # Simple defaults
                st.session_state['bq_dry_run'] = False
                if 'bq_max_bytes_billed' not in st.session_state:
                    st.session_state['bq_max_bytes_billed'] = 100_000_000
                
                # Execute button with callback (proper Streamlit pattern)
                st.form_submit_button(
                    "▶️ Execute Query", 
                    type="primary",
                    help="Execute the SQL query against BigQuery",
                    on_click=execute_sql_callback
                )

        # Handle execution status and display results (outside form)
        handle_sql_execution_status(debug_mode)

        # Add option to clear SQL from session state (outside form)
        if st.button("🗑️ Clear SQL", help="Clear the stored SQL query from session state", key="clear_sql_button"):
            if 'extracted_sql' in st.session_state:
                del st.session_state.extracted_sql
            # Clear execution-related state to allow new processing
            for key in ['sql_execution_result', 'sql_execution_error', 'sql_execution_completed', 'sql_execution_metadata', 'sql_execution_validation']:
                if key in st.session_state:
                    del st.session_state[key]
            logger.info("🗑️ Cleared SQL and execution state from session state")
            st.rerun()
    else:
        # No SQL found case
        if debug_mode:
            st.write("❌ **No SQL available** - cannot show execution interface")
        
        # Check if we had SQL before but lost it
        if 'extracted_sql' in st.session_state and st.session_state.extracted_sql:
            st.warning("⚠️ SQL was previously extracted but is no longer detected in the current answer. You can try regenerating your query.")
            if st.button("🔄 Try to Re-extract SQL", key="reextract_sql_button"):
                # Force re-extraction by clearing session state
                del st.session_state.extracted_sql
                # Clear execution-related state to allow new processing
                for key in ['sql_execution_result', 'sql_execution_error', 'sql_execution_completed', 'sql_execution_metadata', 'sql_execution_validation']:
                    if key in st.session_state:
                        del st.session_state[key]
                logger.info("🔄 Forced SQL re-extraction by clearing session state")
                st.rerun()


def handle_sql_execution_status(debug_mode: bool = False):
    """
    Handle SQL execution status display after form submission
    This runs after the callback and displays appropriate status/results
    """
    # Check if execution is in progress
    if st.session_state.get('sql_executing', False):
        with st.spinner("🔄 Executing SQL query..."):
            st.write("Query execution in progress...")
        return
    
    # Check for execution errors
    if 'sql_execution_error' in st.session_state and st.session_state.sql_execution_error:
        st.error(f"❌ {st.session_state.sql_execution_error}")
        validation_msg = st.session_state.get('sql_execution_validation')
        if validation_msg:
            st.info(f"🛡️ Validation details: {validation_msg}")
        if debug_mode:
            st.write(f"**Error Details**: {st.session_state.sql_execution_error}")
        return
    
    # Display results if available
    if 'sql_execution_result' in st.session_state and st.session_state.sql_execution_result:
        st.divider()
        st.subheader("📊 Query Execution Results")
        
        result = st.session_state.sql_execution_result
        metadata = st.session_state.get('sql_execution_metadata', {})
        validation_msg = st.session_state.get('sql_execution_validation')
        if debug_mode:
            st.write(f"**📊 Result Status**: Success={result.success}, Rows={result.total_rows}")
            if metadata:
                st.write(f"**⚙️ Execution Metadata**: {metadata}")
            if validation_msg:
                st.write(f"**🛡️ Validation Details**: {validation_msg}")
        
        display_sql_execution_results(result)

def execute_sql_callback():
    """
    Callback function for SQL execution - runs BEFORE script rerun
    This follows Streamlit's recommended callback pattern for forms
    """
    try:
        # Get SQL and executor from session state
        sql = st.session_state.get('extracted_sql')
        executor = st.session_state.get('bigquery_executor')
        debug_mode = st.session_state.get('debug_mode', False)
        
        if not sql or not executor:
            st.session_state.sql_execution_error = "SQL or executor not available in session state"
            logger.error("❌ SQL execution callback failed - missing SQL or executor")
            return
        
        # Set execution flag to show spinner on rerun
        st.session_state.sql_executing = True
        st.session_state.sql_execution_error = None
        
        logger.info(f"🔄 [CALLBACK] Starting BigQuery execution for SQL: {sql[:100]}...")
        
        # Execute the query in callback (before rerun)
        # Read execution preferences from session state
        dry_run = bool(st.session_state.get('bq_dry_run', False))
        max_bytes_billed = st.session_state.get('bq_max_bytes_billed', 100_000_000)

        response = run_sql_execution(
            sql,
            executor=executor,
            settings=SQLExecutionSettings(
                project_id=executor.project_id,
                dataset_id=executor.dataset_id,
                dry_run=dry_run,
                max_bytes_billed=max_bytes_billed,
                debug_mode=debug_mode
            )
        )

        if response.success and response.result:
            st.session_state.sql_execution_result = response.result
            st.session_state.sql_execution_error = None
            st.session_state.sql_execution_metadata = response.metadata or {}
            st.session_state.sql_execution_validation = response.validation_message
            logger.info(f"💾 [CALLBACK] Execution completed - Success: {response.result.success}")
        else:
            error_msg = response.error_message or "SQL execution failed."
            st.session_state.sql_execution_result = None
            st.session_state.sql_execution_error = error_msg
            logger.warning(f"❌ [CALLBACK] Execution failed: {error_msg}")
            st.session_state.sql_execution_metadata = response.metadata or {}
            # Propagate validation details for potential UI use
            st.session_state.sql_execution_validation = response.validation_message

        st.session_state.sql_executing = False
        st.session_state.sql_execution_completed = True  # Prevent query reprocessing
            
    except Exception as e:
        error_msg = f"Callback execution error: {str(e)}"
        st.session_state.sql_execution_error = error_msg
        st.session_state.sql_executing = False
        st.session_state.sql_execution_completed = True  # Prevent query reprocessing even on error
        logger.error(f"❌ [CALLBACK] {error_msg}")

# Note: execute_sql_query function removed - now using callback pattern
# All SQL execution happens in execute_sql_callback() before script rerun


def display_sql_execution_results(result: QueryResult):
    """
    Display SQL execution results with comprehensive metrics
    
    Args:
        result: QueryResult object with execution results and metadata
    """
    if result.success:
        st.success("🎉 Query executed successfully!")
        if getattr(result, 'dry_run', False):
            st.info("🧪 Dry run: query not executed. Showing estimated bytes only.")
        
        # Display execution metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📊 Rows Returned",
                f"{result.total_rows:,}",
                help="Number of rows in the result set"
            )
        
        with col2:
            st.metric(
                "⏱️ Execution Time",
                format_execution_time(result.execution_time),
                help="Time taken to execute the query"
            )
        
        with col3:
            st.metric(
                "💾 Data Processed",
                format_bytes(result.bytes_processed),
                help="Amount of data processed by BigQuery"
            )
        
        with col4:
            cache_status = "🎯 Cache Hit" if result.cache_hit else "🔄 Fresh Query"
            st.metric(
                "💰 Data Billed",
                format_bytes(result.bytes_billed),
                delta=cache_status,
                help="Amount of data billed (cached queries are free)"
            )
        
        # Display the actual data (not available for dry runs)
        if (not getattr(result, 'dry_run', False)) and result.data is not None and not result.data.empty:
            st.markdown("**📋 Query Results:**")
            
            # Display data with interactive features
            st.dataframe(
                result.data,
                use_container_width=True,
                hide_index=True
            )
            
            # Export functionality
            csv_data = result.data.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_data,
                file_name=f"bigquery_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Download the query results as a CSV file",
                key="results_download_csv_button"
            )
            
            # Show data info
            with st.expander("ℹ️ Data Information", expanded=False):
                st.markdown(f"**Shape:** {result.data.shape[0]:,} rows × {result.data.shape[1]} columns")
                st.markdown(f"**Job ID:** `{result.job_id}`")
                
                # Show column info
                if len(result.data.columns) > 0:
                    st.markdown("**Columns:**")
                    for col in result.data.columns:
                        dtype = str(result.data[col].dtype)
                        null_count = result.data[col].isnull().sum()
                        st.text(f"  • {col}: {dtype} ({null_count:,} nulls)")
        else:
            st.info("✅ Query executed successfully but returned no data")
    
    else:
        st.error(f"❌ Query execution failed: {result.error_message}")
        
        # Show execution metadata even for failed queries
        if result.execution_time > 0:
            st.caption(f"⏱️ Failed after {format_execution_time(result.execution_time)}")
        
        if result.job_id:
            st.caption(f"📋 Job ID: `{result.job_id}`")












def apply_modern_styling():
    """Apply Duna-inspired modern CSS styling with warm, professional aesthetic"""
    st.markdown("""
    <style>
    /* Import Inter font for modern typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* Base typography improvements */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    h1, h2, h3 {
        font-weight: 800;
        letter-spacing: -0.02em;
    }

    p {
        line-height: 1.7;
    }

    /* Main title - gradient effect */
    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        line-height: 1.1;
        letter-spacing: -0.03em;
        margin-bottom: 1.5rem;
        background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Subtitle styling */
    .subtitle {
        font-size: 1.25rem;
        line-height: 1.6;
        color: #6B7280;
        margin-bottom: 3rem;
        max-width: 600px;
    }

    /* Modern buttons with gradient */
    .stButton > button {
        background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%);
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        color: white;
        box-shadow: 0 4px 16px rgba(139, 92, 246, 0.25);
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 24px rgba(139, 92, 246, 0.35);
    }

    /* Primary button specific styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%);
    }

    /* Metric cards - clean minimal */
    [data-testid="metric-container"] {
        background: #FAFAFA;
        border-radius: 12px;
        padding: 1.5rem;
        border-left: 4px solid #8B5CF6;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }

    /* Progress bars - warm gradient */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #8B5CF6 0%, #EC4899 100%);
        border-radius: 4px;
    }

    /* Code blocks - warm accent */
    .stCodeBlock {
        border-left: 3px solid #8B5CF6;
        background: #FAFAFA;
        border-radius: 8px;
    }

    /* Expanders - clean minimal */
    .streamlit-expanderHeader {
        background: #FAFAFA;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .streamlit-expanderHeader:hover {
        background: #F3F4F6;
    }

    /* Input fields - modern clean */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #E5E7EB;
        transition: all 0.2s ease;
        font-family: 'Inter', sans-serif;
    }

    .stTextInput > div > div > input:focus {
        border-color: #8B5CF6;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
    }

    /* Text area styling */
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 2px solid #E5E7EB;
        transition: all 0.2s ease;
        font-family: 'Inter', sans-serif;
    }

    .stTextArea > div > div > textarea:focus {
        border-color: #8B5CF6;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
    }

    /* Success messages */
    .stSuccess {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        border-radius: 8px;
        border: none;
    }

    /* Info messages */
    .stInfo {
        background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%);
        border-radius: 8px;
        border: none;
    }

    /* Warning messages */
    .stWarning {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        border-radius: 8px;
        border: none;
    }

    /* Error messages */
    .stError {
        background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);
        border-radius: 8px;
        border: none;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: #FAFAFA;
    }

    /* Radio buttons */
    .stRadio > div {
        gap: 0.5rem;
    }

    /* Selectbox styling */
    .stSelectbox > div > div {
        border-radius: 8px;
    }

    /* Dataframe styling */
    .dataframe {
        border-radius: 8px;
        border: 1px solid #E5E7EB;
    }

    /* Chat message styling */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    /* Generous section spacing - Duna style */
    .section-spacing {
        padding: 4rem 0;
    }

    /* Feature cards hover effect */
    .element-container:hover {
        transition: transform 0.2s ease;
    }
    </style>
    """, unsafe_allow_html=True)


def main():
    """Main Streamlit application"""

    # Apply modern Duna-inspired styling
    apply_modern_styling()

    # Header
    st.title("⚡ Ask Data Questions Without SQL")
    st.caption("Get instant answers from your data in plain English—no SQL required. For SQL experts: build queries 10x faster with AI-powered assistance.")
    
    # Load CSV data first (needed for both pages)
    if 'csv_data' not in st.session_state:
        csv_data = load_csv_data()
        if csv_data is not None:
            st.session_state.csv_data = csv_data
        else:
            st.error("Cannot proceed without CSV data")
            st.stop()
    
    # Load schema manager for smart schema injection (cached)
    if 'schema_manager' not in st.session_state:
        schema_manager = load_schema_manager()
        st.session_state.schema_manager = schema_manager
        
        if schema_manager:
            logger.info(f"✅ Schema manager ready: {schema_manager.table_count} tables available for injection")
        else:
            logger.info("Schema manager not available - proceeding without schema injection")
    
    # Load LookML safe-join map for enhanced SQL generation (cached)
    if 'lookml_safe_join_map' not in st.session_state:
        lookml_safe_join_map = load_lookml_safe_join_map()
        st.session_state.lookml_safe_join_map = lookml_safe_join_map
        
        if lookml_safe_join_map:
            total_explores = lookml_safe_join_map.get('metadata', {}).get('total_explores', 0)
            logger.info(f"✅ LookML safe-join map ready: {total_explores} explores available for SQL generation")
        else:
            logger.info("LookML safe-join map not available - proceeding without LookML features")
    
    # Sidebar for navigation and configuration
    with st.sidebar:
        st.header("📱 Navigation")
        
        # Page selection
        page = st.radio(
            "Select Page:",
            ["◆ Introduction", "→ Query Search", "◉ Data", "● Catalog", "◐ Chat"],
            key="page_selection"
        )
        
        # Keep Query Search and Introduction pages minimal; show configuration only for other pages
        if page not in ["→ Query Search", "◆ Introduction"]:
            st.divider()
            st.header("⚙️ Configuration")
            # Advanced mode toggle: simple by default
            default_adv = (os.getenv('UI_ADVANCED_DEFAULT', '0').lower() in ('1', 'true', 'yes'))
            advanced_mode = st.checkbox(
                "Advanced Mode",
                value=st.session_state.get('advanced_mode', default_adv),
                help="Show detailed controls (schema browser, BigQuery settings, metrics)",
                key="advanced_mode_toggle"
            )
            st.session_state.advanced_mode = advanced_mode
        else:
            # Force advanced mode off for a streamlined Query Search and Introduction pages
            st.session_state.advanced_mode = False

        # Show configuration based on selected page
        if page == "→ Query Search":
            # Minimal: silently choose a vector store (no extra UI)
            available_indices = get_available_indices()
            if not available_indices:
                st.error("❌ No vector stores found!")
                st.info("Run standalone_embedding_generator.py first")
                st.stop()

            selected_index = DEFAULT_VECTOR_STORE if DEFAULT_VECTOR_STORE in available_indices else available_indices[0]

        elif page == "◐ Chat":
            # Chat page configuration: conversation management + user context and table exclusions
            
            # Conversation Management Section
            if CONVERSATION_MANAGER_AVAILABLE:
                st.subheader("💾 Conversations")
                
                # Initialize conversation manager and user session
                if 'conversation_manager' not in st.session_state:
                    try:
                        st.session_state.conversation_manager = get_conversation_manager()
                        logger.info("✅ Conversation manager initialized successfully")
                    except Exception as e:
                        logger.error(f"❌ Failed to initialize conversation manager: {e}")
                        st.error("❌ Failed to initialize conversation persistence")
                        st.caption("Conversations will not be saved. Check Cloud configuration.")
                        st.session_state.conversation_manager = None
                
                # Only proceed if conversation manager is available
                if st.session_state.conversation_manager is None:
                    st.warning("⚠️ Conversation persistence unavailable")
                    st.caption("Check Google Cloud Firestore setup and permissions")
                    st.divider()
                    
                else:
                    user_session_id = get_user_session_id()
                    
                    # Display storage status
                    try:
                        storage_status = st.session_state.conversation_manager.get_storage_status()
                        if storage_status['firestore_available']:
                            st.success("☁️ Cloud Storage Active")
                        else:
                            st.warning("💻 Local Storage Only")
                            if storage_status.get('fallback_conversations', 0) > 0:
                                st.caption(f"{storage_status['fallback_conversations']} conversations in memory")
                    except Exception as e:
                        logger.error(f"Error getting storage status: {e}")
                        st.warning("💻 Local Storage Only")
                    
                    # New Conversation Button
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🆕 New Conversation", use_container_width=True, key="new_conversation_button"):
                            # Clear current conversation
                            st.session_state.chat_messages = []
                            st.session_state.token_usage = []
                            if 'current_conversation_id' in st.session_state:
                                del st.session_state.current_conversation_id
                            st.rerun()
                    
                    with col2:
                        # Save Current Conversation Button
                        if st.session_state.get('chat_messages', []):
                            if st.button("💾 Save Conversation", use_container_width=True, key="save_conversation_button"):
                                try:
                                    conv_id = st.session_state.get('current_conversation_id')
                                    saved_id, success = st.session_state.conversation_manager.save_conversation(
                                        messages=st.session_state.chat_messages,
                                        user_session_id=user_session_id,
                                        conversation_id=conv_id
                                    )
                                    if success:
                                        st.session_state.current_conversation_id = saved_id
                                        st.success(f"✅ Conversation saved!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to save conversation")
                                except Exception as e:
                                    logger.error(f"Error saving conversation: {e}")
                                    st.error("❌ Error saving conversation")
                    
                    # Load Conversations Section
                    try:
                        conversations = st.session_state.conversation_manager.list_conversations(
                            user_session_id=user_session_id,
                            limit=20
                        )
                        
                        if conversations:
                            # Search conversations
                            search_term = st.text_input(
                                "🔍 Search conversations:",
                                placeholder="Search by title or tags...",
                                key="conversation_search"
                            )
                            
                            # Filter conversations if search term provided
                            if search_term:
                                try:
                                    filtered_conversations = st.session_state.conversation_manager.list_conversations(
                                        user_session_id=user_session_id,
                                        limit=20,
                                        search_term=search_term
                                    )
                                except Exception as e:
                                    logger.error(f"Error searching conversations: {e}")
                                    filtered_conversations = conversations
                            else:
                                filtered_conversations = conversations
                            
                            # Display conversations
                            if filtered_conversations:
                                st.caption(f"Found {len(filtered_conversations)} conversation(s)")
                                
                                for conv in filtered_conversations:
                                    with st.container():
                                        # Conversation item
                                        col1, col2, col3 = st.columns([3, 1, 1])
                                        
                                        with col1:
                                            # Truncate long titles
                                            display_title = conv.title
                                            if len(display_title) > 40:
                                                display_title = display_title[:37] + "..."
                                            
                                            st.markdown(f"**{display_title}**")
                                            st.caption(f"{conv.message_count} messages • {conv.updated_at.strftime('%m/%d %H:%M')}")
                                        
                                        with col2:
                                            # Load conversation button
                                            if st.button("📂", key=f"load_{conv.conversation_id}", help="Load conversation"):
                                                try:
                                                    # Load conversation data
                                                    conv_data = st.session_state.conversation_manager.load_conversation(
                                                        conversation_id=conv.conversation_id,
                                                        user_session_id=user_session_id
                                                    )
                                                    
                                                    if conv_data:
                                                        st.session_state.chat_messages = conv_data.get('messages', [])
                                                        st.session_state.current_conversation_id = conv.conversation_id
                                                        st.success(f"✅ Loaded: {conv.title}")
                                                        st.rerun()
                                                    else:
                                                        st.error("❌ Failed to load conversation")
                                                except Exception as e:
                                                    logger.error(f"Error loading conversation: {e}")
                                                    st.error("❌ Error loading conversation")
                                        
                                        with col3:
                                            # Delete conversation button
                                            if st.button("🗑️", key=f"delete_{conv.conversation_id}", help="Delete conversation"):
                                                try:
                                                    if st.session_state.conversation_manager.delete_conversation(
                                                        conversation_id=conv.conversation_id,
                                                        user_session_id=user_session_id
                                                    ):
                                                        st.success("✅ Conversation deleted")
                                                        st.rerun()
                                                    else:
                                                        st.error("❌ Failed to delete conversation")
                                                except Exception as e:
                                                    logger.error(f"Error deleting conversation: {e}")
                                                    st.error("❌ Error deleting conversation")
                            else:
                                st.info("No conversations found matching your search")
                        else:
                            st.info("No saved conversations yet")
                            
                    except Exception as e:
                        logger.error(f"Error listing conversations: {e}")
                        st.error("❌ Error loading conversations")
                    
                    st.divider()
            else:
                st.warning("⚠️ Conversation persistence unavailable")
                st.caption("Install google-cloud-firestore to enable conversation saving")
                st.divider()
            
            # User Context & Filters Section
            if SCHEMA_MANAGER_AVAILABLE and st.session_state.get('schema_manager'):
                st.subheader("🧩 User Context & Filters")
                user_context = st.text_area(
                    "Additional Context (optional)",
                    value=st.session_state.get('user_context', ""),
                    help="Add business rules, constraints, or clarifications for the model",
                    height=120,
                    key="user_context_input_chat"
                )
                st.session_state.user_context = user_context

                try:
                    table_options = sorted(list(st.session_state.schema_manager.schema_lookup.keys()))
                except Exception:
                    table_options = []
                excluded_tables = st.multiselect(
                    "Exclude Tables (optional)",
                    options=table_options,
                    default=st.session_state.get('excluded_tables', []),
                    help="Selected tables will be excluded from schema injection and discouraged in generated SQL",
                    key="excluded_tables_select_chat"
                )
                st.session_state.excluded_tables = excluded_tables
            else:
                st.caption("Schema manager not loaded; context filters unavailable.")
        elif page == "● Catalog":
            # Query Catalog page - show data info
            st.subheader("◉ Data Info")
            df = st.session_state.csv_data
            st.metric("Total Queries", len(df))
            st.caption(f"Source: {CSV_PATH.name}")
        elif page == "◉ Data":
            # Schema page - simple summary
            st.subheader("🗃️ Schema Summary")
            sm = st.session_state.get('schema_manager')
            if sm:
                st.metric("Tables", sm.table_count)
                st.metric("Columns", sm.column_count)
                st.caption(f"Schema file: {SCHEMA_CSV_PATH.name}")
            else:
                st.warning("Schema not loaded. Ensure the schema CSV exists.")
    
    # Route to appropriate page
    if page == "◆ Introduction":
        # Introduction page - no prerequisites required
        create_introduction_page()

    elif page == "→ Query Search":
        # Load vector store for search page
        if not available_indices:
            st.error("❌ No vector stores found for search!")
            return
            
        if 'vector_store' not in st.session_state or st.session_state.get('current_index') != selected_index:
            with st.spinner(f"Loading vector store: {selected_index}..."):
                logger.info(f"🗂️ VECTOR DATABASE LOADING")
                logger.info(f"📂 Selected index: {selected_index}")
                logger.info(f"📁 Index path: {FAISS_INDICES_DIR / selected_index}")
                logger.debug(f"[VECTOR DEBUG] Loading vector database: {selected_index}")
                logger.debug(f"[VECTOR DEBUG] Vector store path: {FAISS_INDICES_DIR / selected_index}")
                
                vector_store = load_vector_store(selected_index)
                
                if vector_store:
                    # Prefer FAISS index size, fallback to docstore if available
                    try:
                        doc_count = int(getattr(vector_store, 'index').ntotal)
                    except Exception:
                        try:
                            doc_count = len(vector_store.docstore._dict)
                        except Exception:
                            doc_count = None
                    st.session_state.vector_store = vector_store
                    st.session_state.current_index = selected_index
                    logger.info(f"✅ VECTOR DATABASE LOADED SUCCESSFULLY")
                    logger.info(f"📊 Vector Store Stats:")
                    logger.info(f"   - Total documents: {doc_count:,}")
                    logger.info(f"   - Index name: {selected_index}")
                    provider_info = get_provider_info()
                    try:
                        logger.info(
                            f"   - Embedding provider: {provider_info.get('provider', 'unknown')} "
                            f"({provider_info.get('model', '')})"
                        )
                    except Exception:
                        pass
                    logger.debug(f"[VECTOR DEBUG] Vector database loaded successfully with {doc_count:,} documents")
                    if doc_count is not None:
                        st.success(f"✅ Loaded {doc_count:,} documents")
                    else:
                        st.success("✅ Vector store loaded")
                else:
                    logger.error(f"❌ VECTOR DATABASE LOADING FAILED")
                    logger.error(f"   - Failed index: {selected_index}")
                    logger.debug(f"[VECTOR DEBUG] FAILED to load vector database: {selected_index}")
                    st.error("Failed to load vector store")
                    return
        
        # Simple Query Search UI: Ask → Show SQL → Execute
        st.subheader("❓ Ask a Question")
        simple_query = st.text_input(
            "Enter your question:",
            placeholder="e.g., Write SQL to join users and orders and compute monthly spend",
            key="simple_query_input"
        )
        
        # Enhanced input validation for security
        if simple_query:
            try:
                from security.input_validator import validate_input_legacy_wrapper
                input_valid, input_error = validate_input_legacy_wrapper(simple_query, 'query')
                if not input_valid:
                    st.error(f"🚫 Input validation failed: {input_error}")
                    simple_query = None
            except ImportError:
                # Fallback - basic validation
                if len(simple_query.strip()) > 2000:
                    st.error("🚫 Query too long (max 2000 characters)")
                    simple_query = None

        generate_clicked = st.button("Generate SQL", type="primary", key="simple_generate_sql_button")

        # Clear prior execution/session state on new generation
        if generate_clicked:
            for _k in [
                'sql_execution_completed',
                'sql_executing',
                'sql_execution_error',
                'sql_execution_result',
                'sql_execution_metadata',
                'sql_execution_validation',
                'extracted_sql'
            ]:
                if _k in st.session_state:
                    del st.session_state[_k]

        if generate_clicked and simple_query and simple_query.strip():
            with st.spinner("Generating SQL with Gemini..."):
                service_result = run_query_search(
                    simple_query.strip(),
                    vector_store=st.session_state.vector_store,
                    schema_manager=st.session_state.get('schema_manager'),
                    lookml_safe_join_map=st.session_state.get('lookml_safe_join_map'),
                    settings=QuerySearchSettings(k=20, sql_validation=False)
                )

                if service_result.error:
                    st.error(f"❌ {service_result.error}")
                else:
                    # Persist SQL so the execution interface can reuse it without re-extraction
                    if service_result.sql:
                        st.session_state.extracted_sql = service_result.sql
                    elif 'extracted_sql' in st.session_state:
                        del st.session_state['extracted_sql']

                    # Optionally display the generated narrative answer (if any)
                    if service_result.answer_text:
                        st.markdown("**🧠 Gemini Response:**")
                        st.write(service_result.answer_text)

                    # Show SQL execution interface (will reuse stored SQL)
                    display_sql_execution_interface(service_result.answer_text or service_result.sql or "")

        # If SQL already exists from a prior run, show execution UI persistently
        if (not generate_clicked) and st.session_state.get('extracted_sql'):
            display_sql_execution_interface(st.session_state.extracted_sql)

        # Exit early to keep the page streamlined
        return

        # Display session stats
        display_session_stats()
        
        # Main query interface with right-hand schema panel
        st.subheader("❓ Ask a Question")

        left_col, right_col = st.columns([3, 1])

        with left_col:
            query = st.text_input(
                "Enter your question:",
                placeholder="e.g., Which queries show customer spending analysis with multiple JOINs?",
                key="query_search_input"
            )
            
            # Enhanced input validation for security
            if query:
                try:
                    from security.input_validator import validate_input_legacy_wrapper
                    input_valid, input_error = validate_input_legacy_wrapper(query, 'search')
                    if not input_valid:
                        st.error(f"🚫 Input validation failed: {input_error}")
                        query = None
                except ImportError:
                    # Fallback - basic validation
                    if len(query.strip()) > 500:
                        st.error("🚫 Search term too long (max 500 characters)")
                        query = None

            # Check if we should process the query (not if SQL execution just completed)
            search_clicked = st.button("🔍 Search", type="primary", key="main_search_button")
            should_process_query = bool(search_clicked and query.strip())

            # On new search, clear any previous SQL execution state so we don't block processing
            if search_clicked:
                for _k in [
                    'sql_execution_completed',
                    'sql_executing',
                    'sql_execution_error',
                    'sql_execution_result',
                    'extracted_sql'
                ]:
                    if _k in st.session_state:
                        del st.session_state[_k]

        with right_col:
            if st.session_state.get('advanced_mode', False):
                st.subheader("📚 Tables")
                sm_right = st.session_state.get('schema_manager')
            else:
                sm_right = None
            if sm_right:
                table_filter = st.text_input("Filter", "", key="right_schema_filter", help="Filter tables by name")
                try:
                    all_tables_right = sorted(list(sm_right.schema_lookup.keys()))
                except Exception:
                    all_tables_right = []

                filtered_tables_right = [t for t in all_tables_right if table_filter.lower() in t.lower()] if table_filter else all_tables_right

                # Scrollable container (falls back to plain container if height/border not supported)
                try:
                    sc = st.container(border=True, height=520)
                except TypeError:
                    sc = st.container()

                with sc:
                    max_show = 25
                    for t in filtered_tables_right[:max_show]:
                        fqn = sm_right.get_fqn(t) or t
                        with st.expander(t, expanded=False):
                            st.caption(f"FQN: `{fqn}`")
                            df_right = sm_right.schema_df
                            if df_right is not None:
                                try:
                                    norm = sm_right._normalize_table_name(t)
                                    tbl_df = df_right[df_right['table_id'] == norm][['column', 'datatype']].reset_index(drop=True)
                                    st.dataframe(tbl_df, use_container_width=True, hide_index=True)
                                except Exception:
                                    cols = sm_right.get_table_columns(t)
                                    st.write(", ".join(cols) if cols else "No columns")
                            else:
                                cols = sm_right.get_table_columns(t)
                                st.write(", ".join(cols) if cols else "No columns")

                    if len(filtered_tables_right) > max_show:
                        st.caption(f"Showing first {max_show} of {len(filtered_tables_right)} tables")
            elif st.session_state.get('advanced_mode', False):
                st.info("Load a schema CSV to list tables (data_new/thelook_ecommerce_schema.csv)")
        
        # Advanced query configuration (persisted for potential future UI controls)
        if 'advanced_query_k' not in st.session_state:
            st.session_state.advanced_query_k = 20
        k = max(1, int(st.session_state.get('advanced_query_k', 20)))
        st.session_state.advanced_query_k = k

        if 'advanced_query_gemini_mode' not in st.session_state:
            st.session_state.advanced_query_gemini_mode = False
        gemini_mode = bool(st.session_state.get('advanced_query_gemini_mode', False))
        st.session_state.advanced_query_gemini_mode = gemini_mode

        if 'advanced_query_hybrid_search' not in st.session_state:
            st.session_state.advanced_query_hybrid_search = False
        hybrid_search = bool(st.session_state.get('advanced_query_hybrid_search', False))
        st.session_state.advanced_query_hybrid_search = hybrid_search

        if 'advanced_query_auto_adjust_weights' not in st.session_state:
            st.session_state.advanced_query_auto_adjust_weights = True
        auto_adjust_weights = bool(st.session_state.get('advanced_query_auto_adjust_weights', True))
        st.session_state.advanced_query_auto_adjust_weights = auto_adjust_weights

        if 'advanced_query_query_rewriting' not in st.session_state:
            st.session_state.advanced_query_query_rewriting = False
        query_rewriting = bool(st.session_state.get('advanced_query_query_rewriting', False))
        st.session_state.advanced_query_query_rewriting = query_rewriting

        schema_manager_available = bool(st.session_state.get('schema_manager'))
        if 'advanced_query_schema_injection' not in st.session_state:
            st.session_state.advanced_query_schema_injection = schema_manager_available
        schema_injection = bool(st.session_state.get('advanced_query_schema_injection', schema_manager_available))
        st.session_state.advanced_query_schema_injection = schema_injection

        sql_validation_default = SQL_VALIDATION_AVAILABLE
        if 'advanced_query_sql_validation' not in st.session_state:
            st.session_state.advanced_query_sql_validation = sql_validation_default
        sql_validation = bool(st.session_state.get('advanced_query_sql_validation', sql_validation_default))
        st.session_state.advanced_query_sql_validation = sql_validation

        default_validation_level = ValidationLevel.SCHEMA_STRICT if (SQL_VALIDATION_AVAILABLE and ValidationLevel is not None) else None
        validation_level = st.session_state.get('advanced_query_validation_level', default_validation_level)
        if SQL_VALIDATION_AVAILABLE and ValidationLevel is not None and isinstance(validation_level, str):
            validation_level = getattr(ValidationLevel, validation_level, default_validation_level)
        st.session_state.advanced_query_validation_level = validation_level

        search_weights = None
        search_weights_raw = st.session_state.get('advanced_query_search_weights')
        if (not auto_adjust_weights) and HYBRID_SEARCH_AVAILABLE and isinstance(search_weights_raw, dict):
            try:
                search_weights = SearchWeights(
                    vector_weight=search_weights_raw.get('vector_weight', 0.5),
                    keyword_weight=search_weights_raw.get('keyword_weight', 0.5)
                )
            except Exception:
                search_weights = None

        if 'advanced_query_show_full_queries' not in st.session_state:
            st.session_state.advanced_query_show_full_queries = False
        show_full_queries = bool(st.session_state.get('advanced_query_show_full_queries', False))
        st.session_state.advanced_query_show_full_queries = show_full_queries
        
        if should_process_query:
            # Clear any previous SQL execution completion flag
            if 'sql_execution_completed' in st.session_state:
                del st.session_state.sql_execution_completed
                
            # Step-by-step status indicator for search pipeline
            from contextlib import nullcontext
            advanced_mode = st.session_state.get('advanced_mode', False)
            if advanced_mode:
                try:
                    status_cm = st.status("🔎 Searching and generating answer...", expanded=True)
                except Exception:
                    status_cm = nullcontext()
            else:
                status_cm = nullcontext()

            with (status_cm if advanced_mode else st.spinner("Working...")) as status:
                if advanced_mode and status:
                    st.write("1) Analyzing query & settings...")
                    st.write("2) Retrieving relevant documents...")
                    st.write("3) Injecting relevant schema...")
                    st.write("4) Generating answer with Gemini...")
                    st.write("5) Validating SQL (if present)...")
                try:
                    # Log the incoming query for debugging
                    logger.info(f"🔎 PROCESSING NEW QUERY")
                    logger.info(f"📝 User Query: '{query.strip()}'")
                    logger.info(f"⚙️ Settings: Gemini={gemini_mode}, Hybrid={hybrid_search}, Schema={schema_injection}, SQL_Val={sql_validation}")
                    logger.debug(f"[QUERY DEBUG] Processing query: '{query.strip()}'")
                    logger.debug(f"[QUERY DEBUG] Settings - Gemini: {gemini_mode}, Hybrid: {hybrid_search}, Schema: {schema_injection}, SQL Validation: {sql_validation}")
                    
                    # Check for @schema agent queries first
                    agent_type, clean_question = detect_agent_type(query)
                    if agent_type == "schema":
                        # Handle @schema queries directly without using Gemini/RAG
                        schema_response = handle_schema_query(clean_question, st.session_state.lookml_safe_join_map)
                        
                        # Display schema response
                        st.markdown("### 🗂️ Schema Agent Response")
                        st.markdown(schema_response)
                        
                        # Display agent indicator
                        st.info(f"🤖 **{get_agent_indicator(agent_type)}** - Direct LookML exploration (no Gemini/token usage)")
                        
                        logger.info(f"✅ Schema agent handled query directly: '{clean_question}'")
                        # Skip the rest of the RAG processing by returning early
                    else:
                        # Normal RAG processing for non-@schema queries
                        # Determine schema manager to use
                        schema_manager_to_use = None
                        if schema_injection and st.session_state.schema_manager:
                            schema_manager_to_use = st.session_state.schema_manager
                            logger.info(f"🗃️ SCHEMA INJECTION ENABLED")
                            logger.info(f"📊 Schema Manager Stats:")
                            logger.info(f"   - Total tables available: {schema_manager_to_use.table_count}")
                            logger.info(f"   - Total columns available: {schema_manager_to_use.column_count}")
                            logger.info(f"   - Schema file source: {SCHEMA_CSV_PATH}")
                            logger.debug(f"[SCHEMA DEBUG] Schema injection ENABLED with {schema_manager_to_use.table_count} tables and {schema_manager_to_use.column_count} columns")
                        else:
                            if not schema_injection:
                                logger.info("🚫 Schema injection disabled by user")
                                logger.debug("[SCHEMA DEBUG] Schema injection DISABLED by user setting")
                            elif not st.session_state.schema_manager:
                                logger.info("❌ No schema manager available in session state")
                                logger.debug("[SCHEMA DEBUG] Schema manager NOT AVAILABLE - check if schema file exists and loaded properly")
                            else:
                                logger.info("❓ Schema manager not being used for unknown reason")
                                logger.debug("[SCHEMA DEBUG] Schema manager available but not being used - unknown reason")
                    
                    # Log SQL validation status before RAG call
                    if sql_validation:
                        logger.info(f"✅ SQL VALIDATION ENABLED")
                        logger.info(f"📊 Validation Settings:")
                        logger.info(f"   - Validation level: {validation_level}")
                        logger.debug(f"[SQL VALIDATION DEBUG] SQL validation ENABLED with level: {validation_level}")
                    else:
                        logger.info(f"🚫 SQL VALIDATION DISABLED")
                        logger.debug(f"[SQL VALIDATION DEBUG] SQL validation DISABLED by user setting")
                    
                    # Execute the RAG pipeline via shared service logic
                    service_error = None
                    service_sql = None
                    service_result = run_query_search(
                        query,
                        vector_store=st.session_state.vector_store,
                        schema_manager=schema_manager_to_use,
                        lookml_safe_join_map=st.session_state.get('lookml_safe_join_map'),
                        settings=QuerySearchSettings(
                            k=k,
                            gemini_mode=gemini_mode,
                            hybrid_search=hybrid_search,
                            search_weights=search_weights,
                            auto_adjust_weights=auto_adjust_weights,
                            query_rewriting=query_rewriting,
                            sql_validation=sql_validation,
                            validation_level=validation_level,
                            excluded_tables=st.session_state.get('excluded_tables', []),
                            user_context=st.session_state.get('user_context', "")
                        )
                    )

                    if service_result.error:
                        service_error = service_result.error
                        logger.error(f"❌ Query pipeline error: {service_error}")
                        result = None
                    else:
                        result = (
                            service_result.answer_text,
                            service_result.sources,
                            service_result.usage,
                        )
                        service_sql = service_result.sql
                    
                    if result:
                        answer, sources, token_usage = result
                        answer = answer or ""
                        sources = list(sources or [])
                        token_usage = token_usage or {}
                        if service_sql:
                            st.session_state.extracted_sql = service_sql
                        search_method = token_usage.get('search_method', 'vector')
                        # Update step-by-step status details based on token usage
                        if advanced_mode and status and token_usage:
                            try:
                                st.write(f"✅ Retrieved {token_usage.get('documents_retrieved', 0)} documents in {token_usage.get('retrieval_time', 0):.2f}s")
                                sf = token_usage.get('schema_filtering') or {}
                                if sf.get('enabled', False):
                                    st.write(f"✅ Injected relevant schema for {sf.get('relevant_tables', 0)} table(s)" + (" (no schema found)" if not sf.get('schema_available') else ""))
                                if token_usage.get('generation_time') is not None:
                                    st.write(f"✅ Generated answer in {token_usage.get('generation_time', 0):.2f}s")
                                sv = token_usage.get('sql_validation') or {}
                                if sv.get('enabled', False):
                                    vtime = sv.get('validation_time', 0)
                                    errs = len(sv.get('errors', []) or [])
                                    warns = len(sv.get('warnings', []) or [])
                                    st.write(f"✅ Validated SQL in {vtime:.2f}s ({errs} error(s), {warns} warning(s))")
                                # Mark overall status as complete
                                try:
                                    status.update(label="✅ Search and generation complete", state="complete", expanded=False)
                                except Exception:
                                    pass
                            except Exception:
                                pass
                        
                        # Track token usage
                        if token_usage:
                            st.session_state.token_usage.append(token_usage)
                        
                        # Relevant tables (chips with expanders) before the answer
                        try:
                            if st.session_state.get('advanced_mode', False) and token_usage and token_usage.get('sql_validation', {}).get('enabled'):
                                tables_found_chip = token_usage['sql_validation'].get('tables_found', []) or []
                                if tables_found_chip:
                                    st.subheader("📋 Relevant Tables")
                                    sm_chip = st.session_state.get('schema_manager')
                                    max_chips = 8
                                    for t in tables_found_chip[:max_chips]:
                                        fqn = (sm_chip.get_fqn(t) if sm_chip else None) or t
                                        with st.expander(t, expanded=False):
                                            st.caption(f"FQN: `{fqn}`")
                                            if sm_chip:
                                                dfc = sm_chip.schema_df
                                                if dfc is not None:
                                                    try:
                                                        norm = sm_chip._normalize_table_name(t)
                                                        tbl_df = dfc[dfc['table_id'] == norm][['column', 'datatype']].reset_index(drop=True)
                                                        st.dataframe(tbl_df, use_container_width=True, hide_index=True)
                                                    except Exception:
                                                        cols = sm_chip.get_table_columns(t)
                                                        st.write(", ".join(cols) if cols else "No columns")
                                                else:
                                                    cols = sm_chip.get_table_columns(t)
                                                    st.write(", ".join(cols) if cols else "No columns")
                        except Exception:
                            pass

                        # Display answer
                        st.subheader("📜 Answer")
                        st.write(answer)
                        
                        # Extract SQL now (without rendering the execution UI here)
                        # so the persistent execution section can show the interface once.
                        try:
                            if answer and not st.session_state.get('extracted_sql'):
                                # Prefer executor-based extraction when available
                                extracted_sql = None
                                executor = st.session_state.get('bigquery_executor')
                                if executor:
                                    try:
                                        extracted_sql = executor.extract_sql_from_text(answer)
                                    except Exception:
                                        extracted_sql = None
                                # Fallback: regex extract code-fenced SQL
                                if not extracted_sql:
                                    import re as _re
                                    patterns = [
                                        r"```sql\s*\n(.*?)\n\s*```",
                                        r"```\s*\n(.*?)\n\s*```",
                                    ]
                                    for pat in patterns:
                                        m = _re.search(pat, answer, _re.DOTALL | _re.IGNORECASE)
                                        if m:
                                            candidate = m.group(1).strip()
                                            up = candidate.upper()
                                            if (up.startswith(('SELECT', 'WITH')) and ('FROM' in up or ' AS ' in up)):
                                                extracted_sql = candidate
                                                break
                                if extracted_sql:
                                    st.session_state.extracted_sql = extracted_sql
                                    logger.info(f"💾 Extracted and stored new SQL in session state: {extracted_sql[:50]}...")
                        except Exception as _e:
                            logger.debug(f"SQL extraction skipped: {_e}")
                        
                        # SQL Execution UI is rendered in the persistent section below
                        
                        # Display context utilization (Gemini optimization)
                        if sources and gemini_mode:
                            context_stats = calculate_context_utilization(sources, query)
                            
                            # Color coding based on utilization
                            utilization = context_stats['utilization_percent']
                            
                            if utilization < 10:
                                color = "🔴"  # Very low utilization
                                status = "Low utilization - consider increasing K for better results"
                            elif utilization < 50:
                                color = "🟡"  # Moderate utilization
                                status = "Moderate utilization - good balance"
                            else:
                                color = "🟢"  # Good utilization
                                status = "Excellent context utilization"
                            
                            st.subheader(f"{color} Context Utilization")
                            
                            # Progress bar for context utilization
                            st.progress(min(utilization / 100, 1.0))
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric(
                                    label="📊 Context Usage",
                                    value=f"{utilization:.1f}%",
                                    delta=f"{context_stats['total_input_tokens']:,} tokens",
                                    help="Percentage of Gemini's 1M token context window used"
                                )
                            
                            with col2:
                                st.metric(
                                    label="📚 Chunks Retrieved", 
                                    value=context_stats['chunks_used'],
                                    delta=f"~{context_stats['avg_tokens_per_chunk']:.0f} tokens/chunk",
                                    help="Number of relevant chunks with smart deduplication"
                                )
                            
                            with col3:
                                remaining_tokens = 1000000 - context_stats['total_input_tokens']
                                st.metric(
                                    label="🚀 Remaining Capacity",
                                    value=f"{remaining_tokens:,}",
                                    delta="tokens available",
                                    help="Additional tokens available in Gemini's context window"
                                )
                            
                            st.caption(f"💡 {status}")
                        
                        # Display query rewriting information if available
                        if token_usage and token_usage.get('query_rewriting', {}).get('enabled'):
                            st.divider()
                            
                            rewrite_info = token_usage['query_rewriting']
                            st.subheader("🔄 Query Enhancement")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**Original Query:**")
                                st.code(query, language="text")
                            
                            with col2:
                                st.markdown("**Enhanced Query:**")
                                st.code(rewrite_info['rewritten_query'], language="text")
                            
                            # Query rewriting metrics
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric(
                                    "🎯 Enhancement",
                                    "Enhanced" if rewrite_info['query_changed'] else "Original",
                                    f"Confidence: {rewrite_info['confidence']:.2f}"
                                )
                            
                            with col2:
                                model_info = rewrite_info.get('model_used', 'gemini-2.5-flash')
                                st.metric(
                                    "⚡ Rewrite Time",
                                    f"{rewrite_info['rewrite_time']:.3f}s",
                                    f"Model: {model_info.split('-')[-1].upper()}"  # Show just Flash/Pro/Lite
                                )
                            
                            with col3:
                                improvement_estimate = "25-40%" if rewrite_info['query_changed'] else "N/A"
                                st.metric(
                                    "📈 Expected Improvement",
                                    improvement_estimate,
                                    "Retrieval precision"
                                )
                            
                            if rewrite_info['query_changed']:
                                st.success("✅ Query was enhanced with SQL terminology and domain concepts")
                            else:
                                st.info("ℹ️ Original query was already well-optimized")
                        
                        # Display schema filtering information if available
                        if token_usage and token_usage.get('schema_filtering', {}).get('enabled'):
                            st.divider()
                            
                            schema_info = token_usage['schema_filtering']
                            st.subheader("🗃️ Smart Schema Injection")
                            
                            # Schema filtering metrics
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric(
                                    "📊 Tables Identified",
                                    schema_info.get('relevant_tables', 0),
                                    f"Coverage: {schema_info.get('schema_coverage', '0/0')}"
                                )
                            
                            with col2:
                                schema_tokens = schema_info.get('schema_tokens', 0)
                                st.metric(
                                    "🧾 Schema Tokens",
                                    f"{schema_tokens:,}",
                                    "Added to context"
                                )
                            
                            with col3:
                                total_tables = schema_info.get('total_schema_tables', 0)
                                reduction_factor = f"{total_tables:,} → {schema_info.get('relevant_tables', 0)}"
                                st.metric(
                                    "🎯 Noise Reduction",
                                    "99%+" if schema_info.get('relevant_tables', 0) > 0 else "N/A",
                                    reduction_factor
                                )
                            
                            if schema_info.get('schema_available'):
                                st.success("✅ Relevant database schema injected for accurate answers")
                            else:
                                st.info("ℹ️ No matching schema found for identified tables")
                        
                        # Display SQL validation information if available
                        if token_usage and token_usage.get('sql_validation', {}).get('enabled'):
                            st.divider()
                            
                            validation_info = token_usage['sql_validation']
                            st.subheader("✅ SQL Query Validation")
                            
                            # Add comprehensive logging for SQL validation data
                            logger.info(f"🔍 SQL VALIDATION RESULTS")
                            logger.info(f"📊 Validation Summary:")
                            logger.info(f"   - Validation enabled: True")
                            logger.info(f"   - Validation level: {validation_info.get('validation_level', 'basic')}")
                            logger.info(f"   - Is valid: {validation_info.get('is_valid', False)}")
                            logger.info(f"   - Validation time: {validation_info.get('validation_time', 0):.3f}s")
                            
                            logger.debug(f"[SQL VALIDATION DEBUG] SQL Validation ENABLED")
                            logger.debug(f"[SQL VALIDATION DEBUG] Validation level: {validation_info.get('validation_level', 'basic')}")
                            logger.debug(f"[SQL VALIDATION DEBUG] Query is valid: {validation_info.get('is_valid', False)}")
                            
                            # Log detailed validation data
                            tables_found = validation_info.get('tables_found', [])
                            columns_found = validation_info.get('columns_found', [])
                            errors = validation_info.get('errors', [])
                            warnings = validation_info.get('warnings', [])
                            
                            if tables_found:
                                logger.info(f"📋 Tables Found ({len(tables_found)}): {', '.join(tables_found)}")
                                logger.debug(f"[SQL VALIDATION DEBUG] Tables found ({len(tables_found)}): {', '.join(tables_found)}")
                                # UI: Show relevant tables and FQNs (if available)
                                try:
                                    st.markdown("**📋 Relevant Tables Detected:**")
                                    st.write(
                                        ", ".join([f"`{t}`" for t in tables_found]) if tables_found else "None"
                                    )
                                    sm_ui = st.session_state.get('schema_manager')
                                    if sm_ui:
                                        fqn_map_ui = sm_ui.get_fqn_map(tables_found)
                                        if fqn_map_ui:
                                            st.caption("FQN Mapping (use in FROM/JOIN):")
                                            fqn_lines = [f"- {t} → `{fqn}`" for t, fqn in fqn_map_ui.items()]
                                            st.markdown("\n".join(fqn_lines))
                                except Exception:
                                    pass
                            
                            if columns_found:
                                logger.info(f"📊 Columns Found ({len(columns_found)}): {', '.join(str(col) for col in columns_found)}")
                                logger.debug(f"[SQL VALIDATION DEBUG] Columns found ({len(columns_found)}): {', '.join(str(col) for col in columns_found)}")
                            
                            if errors:
                                logger.warning(f"❌ Validation Errors ({len(errors)}):")
                                for i, error in enumerate(errors, 1):
                                    logger.warning(f"   {i}. {error}")
                                logger.debug(f"[SQL VALIDATION DEBUG] ERRORS ({len(errors)}): {errors}")
                            
                            if warnings:
                                logger.warning(f"⚠️ Validation Warnings ({len(warnings)}):")
                                for i, warning in enumerate(warnings, 1):
                                    logger.warning(f"   {i}. {warning}")
                                logger.debug(f"[SQL VALIDATION DEBUG] WARNINGS ({len(warnings)}): {warnings}")
                            
                            # Validation status
                            if validation_info.get('is_valid'):
                                st.success("🎉 Generated SQL is valid!")
                            else:
                                st.error("❌ SQL validation found issues")
                            
                            # Validation metrics
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                tables_found = validation_info.get('tables_found', [])
                                st.metric(
                                    "📋 Tables Validated",
                                    len(tables_found),
                                    f"Level: {validation_info.get('validation_level', 'basic')}"
                                )
                            
                            with col2:
                                columns_found = validation_info.get('columns_found', [])
                                st.metric(
                                    "📊 Columns Validated",
                                    len(columns_found),
                                    f"Time: {validation_info.get('validation_time', 0):.3f}s"
                                )
                            
                            with col3:
                                error_count = len(validation_info.get('errors', []))
                                warning_count = len(validation_info.get('warnings', []))
                                status = "Valid" if validation_info.get('is_valid') else f"{error_count} errors"
                                st.metric(
                                    "🛡️ Validation Status",
                                    status,
                                    f"{warning_count} warnings"
                                )
                            
                            # Show detailed validation results
                            if validation_info.get('errors') or validation_info.get('warnings'):
                                with st.expander("🔍 Validation Details", expanded=validation_info.get('has_errors', False)):
                                    if validation_info.get('errors'):
                                        st.markdown("**❌ Errors:**")
                                        for error in validation_info['errors']:
                                            st.error(f"• {error}")
                                    
                                    if validation_info.get('warnings'):
                                        st.markdown("**⚠️ Warnings:**")
                                        for warning in validation_info['warnings']:
                                            st.warning(f"• {warning}")
                                    
                                    if validation_info.get('suggestions'):
                                        st.markdown("**💡 Suggestions:**")
                                        for suggestion in validation_info['suggestions']:
                                            st.info(f"• {suggestion}")
                            
                            # Show validated schema elements
                            if tables_found or columns_found:
                                with st.expander("📋 Validated Schema Elements", expanded=False):
                                    if tables_found:
                                        st.markdown("**Tables Found:**")
                                        st.code(", ".join(tables_found))
                                    
                                    if columns_found:
                                        st.markdown("**Columns Found:**")
                                        st.code(", ".join(str(col) for col in columns_found))
                                    
                                    joins_found = validation_info.get('joins_found', [])
                                    if joins_found:
                                        st.markdown(f"**Joins Found:** {len(joins_found)}")
                            
                            if validation_info.get('is_valid'):
                                st.success("✅ SQL syntax is correct and all referenced tables/columns exist in schema")
                            else:
                                st.error("🚫 SQL validation failed - please review errors above")
                        
                        # Display enhanced search and token usage information
                        if token_usage:
                            st.divider()
                            
                            # Search method information
                            search_method = token_usage.get('search_method', 'vector')
                            
                            if search_method == 'hybrid' and token_usage.get('hybrid_search_breakdown'):
                                st.subheader("🔀 Hybrid Search Results")
                                breakdown = token_usage['hybrid_search_breakdown']
                                
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.metric(
                                        "🔀 Hybrid Results", 
                                        breakdown.get('hybrid', 0),
                                        "Found by both methods"
                                    )
                                
                                with col2:
                                    st.metric(
                                        "🎯 Vector Only", 
                                        breakdown.get('vector', 0),
                                        "Semantic similarity"
                                    )
                                
                                with col3:
                                    st.metric(
                                        "🔍 Keyword Only", 
                                        breakdown.get('keyword', 0),
                                        "Exact term matching"
                                    )
                                
                                # Show search weights if available
                                if token_usage.get('search_weights'):
                                    weights = token_usage['search_weights']
                                    st.caption(f"🎛️ Search weights: Vector {weights['vector_weight']:.2f}, Keyword {weights['keyword_weight']:.2f}")
                                elif auto_adjust_weights:
                                    st.caption("🤖 Weights auto-adjusted based on query analysis")
                            
                            # Token usage metrics
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric(
                                    "🪙 Response Tokens", 
                                    f"{token_usage['total_tokens']:,}",
                                    f"In: {token_usage['prompt_tokens']:,} | Out: {token_usage['completion_tokens']:,}"
                                )
                            
                            with col2:
                                mode_label = "🔥 Gemini Mode" if gemini_mode else "🏠 Standard Mode"
                                search_label = f" + {search_method.title()}" if search_method != 'vector' else ""
                                st.metric(f"{mode_label}{search_label}", "Google Gemini 2.5 Flash", "Google AI")
                            
                            with col3:
                                retrieval_time = token_usage.get('retrieval_time', 0)
                                docs_processed = token_usage.get('documents_processed', len(sources))
                                st.metric(
                                    "⚡ Performance",
                                    f"{retrieval_time:.2f}s",
                                    f"{docs_processed} docs processed"
                                )
                        
                        # Display sources
                        if sources:
                            st.divider()
                            
                            if show_full_queries:
                                # Show full query cards
                                st.subheader("📋 Source Queries")
                                st.caption(f"Found {len(sources)} relevant chunks from the following complete queries:")
                                
                                # Map sources back to original queries
                                original_queries = find_original_queries_for_sources(sources, st.session_state.csv_data)
                                
                                if original_queries:
                                    for i, query_row in enumerate(original_queries):
                                        st.subheader(f"📄 Source Query {i + 1}")
                                        display_query_card(query_row, i)
                                        
                                        # Show which chunks came from this query
                                        matching_chunks = []
                                        query_content = safe_get_value(query_row, 'query').strip().lower()
                                        
                                        for j, doc in enumerate(sources, 1):
                                            chunk_content = doc.page_content.strip().lower()
                                            if chunk_content in query_content or query_content in chunk_content:
                                                matching_chunks.append(f"Chunk {j}")
                                        
                                        if matching_chunks:
                                            st.caption(f"🔗 Related chunks: {', '.join(matching_chunks)}")
                                        
                                        if i < len(original_queries) - 1:
                                            st.divider()
                                else:
                                    st.warning("Could not map sources back to original queries")
                                    st.info("💡 Falling back to chunk display...")
                                    
                                    # Fallback to chunk display
                                    st.subheader("📂 Source Chunks")
                                    for i, doc in enumerate(sources, 1):
                                        with st.expander(f"Chunk {i}: {doc.metadata.get('source', 'Unknown')}"):
                                            st.code(doc.page_content, language="sql")
                                            
                                            # Show metadata if available
                                            metadata = doc.metadata
                                            if metadata.get('description'):
                                                st.caption(f"**Description:** {metadata['description']}")
                                            if metadata.get('table'):
                                                st.caption(f"**Tables:** {metadata['table']}")
                            else:
                                # Show original chunk display
                                st.subheader("📂 Source Chunks")
                                st.caption(f"Showing {len(sources)} relevant chunks (enable 'Show Full Query Cards' to see complete queries)")
                                
                                for i, doc in enumerate(sources, 1):
                                    with st.expander(f"Chunk {i}: {doc.metadata.get('source', 'Unknown')}"):
                                        st.code(doc.page_content, language="sql")
                                        
                                        # Show metadata if available
                                        metadata = doc.metadata
                                        if metadata.get('description'):
                                            st.caption(f"**Description:** {metadata['description']}")
                                        if metadata.get('table'):
                                            st.caption(f"**Tables:** {metadata['table']}")
                        else:
                            st.warning("No relevant sources found")
                            
                    else:
                        error_message = service_error or "Failed to generate answer"
                        st.error(f"❌ {error_message}")
                        
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    logger.error(f"Query error: {e}")
        
        # Display persistent SQL execution results (outside query processing)
        # This ensures results are shown even when query processing is skipped
        if ('sql_execution_result' in st.session_state or 
            'sql_execution_error' in st.session_state or
            'extracted_sql' in st.session_state):
            
            st.divider()
            st.subheader("💾 Persistent SQL Execution Interface")
            
            # Show SQL execution interface for any existing SQL
            if 'extracted_sql' in st.session_state and st.session_state.extracted_sql:
                display_sql_execution_interface(st.session_state.extracted_sql)
            
            # Results are displayed inside the execution interface via status handler
            
            # Show execution errors if they exist
            if 'sql_execution_error' in st.session_state and st.session_state.sql_execution_error:
                st.error(f"❌ Previous execution error: {st.session_state.sql_execution_error}")
        
        # Instructions
        if not query:
            st.markdown(f"""
            ### 💡 How to Get Started:

            **🎯 For Business Users (No SQL needed):**
            1. Type your question in plain English above
            2. Click "Generate SQL"
            3. Review the results—we handle the SQL for you!

            **⚡ For SQL Experts (Boost your speed):**
            1. Describe what you need in natural language
            2. Get production-ready SQL with joins, validation, and schema
            3. Execute directly against BigQuery—iterate in seconds

            ### 🚀 Why This Works:

            **For non-technical users:**
            - ✨ **No SQL required**: Ask questions naturally, get instant answers
            - 🎯 **Self-service**: Stop depending on data teams for simple queries
            - 📊 **Learn as you go**: See the SQL we generate, understand your data better

            **For SQL professionals:**
            - ⚡ **10x faster**: Complex queries in seconds, not hours
            - ✅ **Production-ready**: Automatic validation catches errors before execution
            - 🤖 **AI pair programmer**: Schema suggestions, join recommendations, optimization tips
            - 📚 **Learn patterns**: Browse 100+ examples to level up your SQL skills

            ### 🔧 Advanced Features:

            **Smart SQL Generation:**
            - Automatic schema injection for accurate table and column names
            - Multi-table join recommendations based on relationships
            - Production-ready queries with proper formatting and best practices

            **Built-in Safety:**
            - Syntax and schema validation before execution
            - Read-only BigQuery access prevents data modifications
            - Cost estimation and result size limits

            **Performance & Results:**
            - Execute queries directly against BigQuery datasets
            - Interactive result tables with sorting and filtering
            - Export results as CSV for further analysis
            - Real-time performance metrics and execution stats
            """)

    elif page == "◐ Chat":
        # Chat page - requires vector store
        available_indices = get_available_indices()
        if not available_indices:
            st.error("❌ No vector stores found for chat!")
            st.info("Run standalone_embedding_generator.py first")
            return
            
        # Use default vector store for chat
        selected_index = available_indices[0] if DEFAULT_VECTOR_STORE not in available_indices else DEFAULT_VECTOR_STORE
        
        # Load vector store for chat page
        if 'vector_store' not in st.session_state or st.session_state.get('current_index') != selected_index:
            with st.spinner(f"Loading vector store for chat: {selected_index}..."):
                vector_store = load_vector_store(selected_index)
                
                if vector_store:
                    st.session_state.vector_store = vector_store
                    st.session_state.current_index = selected_index
                    try:
                        doc_count = int(getattr(vector_store, 'index').ntotal)
                    except Exception:
                        try:
                            doc_count = len(vector_store.docstore._dict)
                        except Exception:
                            doc_count = None
                    if doc_count is not None:
                        st.success(f"✅ Loaded {doc_count:,} documents")
                    else:
                        st.success("✅ Vector store loaded")
                else:
                    st.error("Failed to load vector store")
                    return
        
        # Set chat function reference in session_state for UI pages to access
        st.session_state._answer_question_chat_mode = answer_question_chat_mode
        
        # Create chat page
        create_chat_page(st.session_state.vector_store, st.session_state.csv_data)

    elif page == "● Catalog":
        # Query Catalog page - MANDATORY cache requirement
        # Check for analytics cache before proceeding
        if not CATALOG_ANALYTICS_DIR.exists():
            st.error("🚫 **Query Catalog requires pre-computed analytics**")
            st.error(f"❌ Analytics cache directory not found: `{CATALOG_ANALYTICS_DIR}`")
            st.code("""
# Generate analytics cache first:
python catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv"
            """)
            st.info("💡 This will create optimized data files for instant loading")
            st.stop()
        
        # Check for required cache files
        required_files = [
            "join_analysis.json",
            "cache_metadata.json", 
            "optimized_queries.parquet"
        ]
        
        missing_files = []
        for file_name in required_files:
            if not (CATALOG_ANALYTICS_DIR / file_name).exists():
                missing_files.append(file_name)
        
        if missing_files:
            st.error("🚫 **Incomplete analytics cache**")
            st.error(f"❌ Missing files: {', '.join(missing_files)}")
            st.code("""
# Regenerate complete analytics cache:
python catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv" --force-rebuild
            """)
            st.stop()
        
        # All checks passed - proceed with catalog page
        create_query_catalog_page(st.session_state.csv_data)

    elif page == "◉ Data":
        # Render data schema browser
        create_data_page(st.session_state.get('schema_manager'))

if __name__ == "__main__":
    main()
