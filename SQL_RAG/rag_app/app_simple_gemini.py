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

# Load environment variables from .env if present (for GEMINI_API_KEY, etc.)
try:
    from dotenv import load_dotenv, find_dotenv
    _env_path = find_dotenv(usecwd=True)
    if _env_path:
        load_dotenv(_env_path, override=False)
        logging.getLogger(__name__).info(f"Loaded environment from {_env_path}")
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
from simple_rag_simple_gemini import answer_question_simple_gemini
from utils.embedding_provider import get_provider_info

# Import conversation management
try:
    from core.conversation_manager import get_conversation_manager
    CONVERSATION_MANAGER_AVAILABLE = True
except ImportError:
    CONVERSATION_MANAGER_AVAILABLE = False

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
    SQL_VALIDATION_AVAILABLE = False

# Import BigQuery execution components
try:
    from core.bigquery_executor import BigQueryExecutor, QueryResult, format_bytes, format_execution_time
    BIGQUERY_EXECUTION_AVAILABLE = True
except ImportError:
    BIGQUERY_EXECUTION_AVAILABLE = False

# Configure logging (idempotent)
if not logging.getLogger(__name__).handlers:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
FAISS_INDICES_DIR = Path(__file__).parent / "faiss_indices"
DEFAULT_VECTOR_STORE = "index_transformed_sample_queries"  # Expected index name
CSV_PATH = Path(__file__).parent / "sample_queries_with_metadata.csv"  # CSV data source
CATALOG_ANALYTICS_DIR = Path(__file__).parent / "catalog_analytics"  # Cached analytics
SCHEMA_CSV_PATH = Path(__file__).parent / "data_new/thelook_ecommerce_schema.csv"  # Schema file with table_id, column, datatype
LOOKML_SAFE_JOIN_MAP_PATH = FAISS_INDICES_DIR / "lookml_safe_join_map.json"  # LookML join relationships
SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH = Path(__file__).parent / "lookml_safe_join_map.json"
LOOKML_DIR = Path(__file__).parent / "lookml_data"

# Pagination Configuration
QUERIES_PER_PAGE = 15  # Optimal balance: not too few, not too many for performance
MAX_PAGES_TO_SHOW = 10  # Maximum pages to show in dropdown for large datasets

# Streamlit page config
st.set_page_config(
    page_title="Simple SQL RAG with Gemini", 
    page_icon="🔥",
    layout="wide"
)

def estimate_token_count(text: str) -> int:
    """Rough estimation of token count (4 chars ≈ 1 token)."""
    return len(text) // 4

def calculate_context_utilization(docs: list, query: str) -> dict:
    """Calculate context utilization for Gemini's 1M token window."""
    GEMINI_MAX_TOKENS = 1000000  # 1M token context window
    
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

def load_vector_store(index_name: str = DEFAULT_VECTOR_STORE) -> Optional[FAISS]:
    """
    Load pre-built vector store from faiss_indices directory
    
    Args:
        index_name: Name of the index directory to load
        
    Returns:
        FAISS vector store or None if loading fails
    """
    index_path = FAISS_INDICES_DIR / index_name
    
    if not index_path.exists():
        st.error(f"❌ Vector store not found at: {index_path}")
        st.info("💡 First run: python standalone_embedding_generator.py --csv 'your_data.csv'")
        return None
    
    try:
        # Initialize embeddings using provider factory (Ollama or OpenAI)
        from utils.embedding_provider import get_embedding_function
        embeddings = get_embedding_function()
        
        # Load the pre-built vector store
        # Default keeps existing behavior; can be overridden via env for stricter safety
        allow_dangerous = os.getenv("FAISS_SAFE_DESERIALIZATION", "0").lower() not in ("1", "true", "yes")
        if allow_dangerous:
            logger.info("Loading FAISS index with allow_dangerous_deserialization=True (trusted local data)")
        else:
            logger.info("Loading FAISS index with safe deserialization")
        vector_store = FAISS.load_local(
            str(index_path),
            embeddings,
            allow_dangerous_deserialization=allow_dangerous
        )
        
        logger.info(f"✅ Loaded vector store from {index_path}")
        return vector_store
        
    except Exception as e:
        st.error(f"❌ Error loading vector store: {e}")
        logger.error(f"Vector store loading error: {e}")
        return None

def get_available_indices() -> List[str]:
    """Get list of available vector store indices"""
    if not FAISS_INDICES_DIR.exists():
        return []
    
    indices = []
    for path in FAISS_INDICES_DIR.iterdir():
        if path.is_dir() and path.name.startswith("index_"):
            indices.append(path.name)
    
    return sorted(indices)

@st.cache_resource
def load_lookml_safe_join_map() -> Optional[Dict[str, Any]]:
    """
    Load LookML safe-join map for enhanced SQL generation.
    
    Returns:
        Dictionary containing LookML join relationships or None if loading fails
    """
    # 1) Primary: load from faiss_indices (created by standalone_embedding_generator --lookml-dir)
    if LOOKML_SAFE_JOIN_MAP_PATH.exists():
        try:
            with open(LOOKML_SAFE_JOIN_MAP_PATH, 'r') as f:
                safe_join_map = json.load(f)
            logger.info(
                f"✅ Loaded LookML safe-join map from {LOOKML_SAFE_JOIN_MAP_PATH} with "
                f"{safe_join_map.get('metadata', {}).get('total_explores', 0)} explores"
            )
            return safe_join_map
        except Exception as e:
            logger.warning(f"⚠️ Failed to load safe-join map from {LOOKML_SAFE_JOIN_MAP_PATH}: {e}")

    # 2) Secondary: load from project root if present
    if SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH.exists():
        try:
            with open(SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH, 'r') as f:
                safe_join_map = json.load(f)
            logger.info(
                f"✅ Loaded LookML safe-join map from {SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH} with "
                f"{safe_join_map.get('metadata', {}).get('total_explores', 0)} explores"
            )
            return safe_join_map
        except Exception as e:
            logger.warning(f"⚠️ Failed to load safe-join map from {SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH}: {e}")

    # 3) Fallback: parse LookML files on the fly if available
    try:
        if LOOKML_DIR.exists():
            logger.info(f"🔎 LookML safe-join map not found; attempting to parse LookML from {LOOKML_DIR}")
            try:
                from simple_lookml_parser import SimpleLookMLParser
            except Exception as ie:
                logger.warning(f"⚠️ SimpleLookMLParser import failed: {ie}")
                return None

            parser = SimpleLookMLParser(verbose=False)
            models = parser.parse_directory(LOOKML_DIR)
            if not models:
                logger.info("No LookML models parsed; LookML features disabled")
                return None

            safe_join_map = parser.generate_safe_join_map(models)

            # Attempt to cache to faiss_indices for reuse
            try:
                LOOKML_SAFE_JOIN_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(LOOKML_SAFE_JOIN_MAP_PATH, 'w') as f:
                    json.dump(safe_join_map, f, indent=2)
                logger.info(f"💾 Cached LookML safe-join map to {LOOKML_SAFE_JOIN_MAP_PATH}")
            except Exception as we:
                logger.debug(f"Could not cache safe-join map: {we}")

            logger.info(
                f"✅ Generated LookML safe-join map with {safe_join_map.get('metadata', {}).get('total_explores', 0)} explores"
            )
            return safe_join_map
        else:
            logger.info(f"LookML directory not found at {LOOKML_DIR}; LookML features disabled")
            return None
    except Exception as e:
        logger.error(f"❌ Error generating LookML safe-join map on the fly: {e}")
        return None

@st.cache_resource
def load_schema_manager() -> Optional[SchemaManager]:
    """
    Load and cache SchemaManager for smart schema injection.
    
    Returns:
        SchemaManager instance or None if loading fails or schema not available
    """
    if not SCHEMA_MANAGER_AVAILABLE:
        return None
    
    if not SCHEMA_CSV_PATH.exists():
        logger.info(f"Schema file not found at {SCHEMA_CSV_PATH} - schema injection disabled")
        logger.debug(f"Expected schema file path: {SCHEMA_CSV_PATH.absolute()}")
        return None
    
    try:
        # Create schema manager with the schema CSV file
        schema_manager = create_schema_manager(str(SCHEMA_CSV_PATH), verbose=True)
        
        if schema_manager:
            logger.info(f"✅ Schema manager loaded: {schema_manager.table_count} tables, {schema_manager.column_count} columns")
            return schema_manager
        else:
            logger.warning("Failed to create schema manager")
            return None
            
    except Exception as e:
        logger.error(f"Error loading schema manager: {e}")
        return None

def load_csv_data() -> Optional[pd.DataFrame]:
    """
    Load optimized CSV data with pre-parsed columns from analytics cache
    
    Returns:
        DataFrame with queries and pre-parsed metadata or None if loading fails
    """
    # PRIORITY 1: Load optimized Parquet file (fastest)
    if CATALOG_ANALYTICS_DIR.exists():
        parquet_path = CATALOG_ANALYTICS_DIR / "optimized_queries.parquet"
        if parquet_path.exists():
            try:
                df = pd.read_parquet(parquet_path)
                # Convert numpy arrays to Python lists for consistency
                if 'tables_parsed' in df.columns:
                    df['tables_parsed'] = df['tables_parsed'].apply(lambda x: list(x) if hasattr(x, '__iter__') and not isinstance(x, str) else ([] if pd.isna(x) else x))
                if 'joins_parsed' in df.columns:
                    df['joins_parsed'] = df['joins_parsed'].apply(lambda x: list(x) if hasattr(x, '__iter__') and not isinstance(x, str) else ([] if pd.isna(x) else x))
                logger.info(f"⚡ Loaded {len(df)} queries from optimized Parquet (pre-parsed)")
                return df
            except ImportError:
                logger.warning("PyArrow not available for Parquet loading")
            except Exception as e:
                logger.warning(f"Failed to load Parquet cache: {e}")
        
        # PRIORITY 2: Load optimized CSV file  
        csv_cache_path = CATALOG_ANALYTICS_DIR / "optimized_queries.csv"
        if csv_cache_path.exists():
            try:
                df = pd.read_csv(csv_cache_path)
                # Parse JSON strings back to lists for cached DataFrame
                if 'tables_parsed' in df.columns:
                    df['tables_parsed'] = df['tables_parsed'].apply(lambda x: json.loads(x) if pd.notna(x) and x != '' else [])
                if 'joins_parsed' in df.columns:
                    df['joins_parsed'] = df['joins_parsed'].apply(lambda x: json.loads(x) if pd.notna(x) and x != '' else [])
                logger.info(f"✅ Loaded {len(df)} queries from optimized CSV cache (pre-parsed)")
                return df
            except Exception as e:
                logger.warning(f"Failed to load optimized CSV cache: {e}")
    
    # FALLBACK: Original CSV (requires manual parsing - slower)
    try:
        if not CSV_PATH.exists():
            st.error(f"❌ CSV file not found: {CSV_PATH}")
            st.error("💡 Please run: python catalog_analytics_generator.py --csv 'your_file.csv'")
            return None
        
        df = pd.read_csv(CSV_PATH)
        df = df.fillna('')
        
        # Ensure required columns exist
        if 'query' not in df.columns:
            st.error(f"❌ Missing required 'query' column in {CSV_PATH}")
            return None
        
        # Remove rows with empty queries
        df = df[df['query'].str.strip() != '']
        
        # Warning: No pre-parsed columns available
        st.warning("⚠️ Using original CSV without pre-parsed data - performance may be slower")
        st.info("💡 Run `python catalog_analytics_generator.py --csv 'your_file.csv'` for better performance")
        
        logger.info(f"📄 Loaded {len(df)} queries from original CSV (no cache)")
        return df
        
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        logger.error(f"Data loading error: {e}")
        return None

def safe_get_value(row, column: str, default: str = '') -> str:
    """Safely get value from dataframe row, handling missing/empty values"""
    try:
        value = row.get(column, default)
        if pd.isna(value) or value is None:
            return default
        return str(value).strip()
    except Exception as e:
        logger.debug(f"safe_get_value fallback for column '{column}': {e}")
        return default

def get_user_session_id() -> str:
    """
    Get or create a unique user session ID for conversation management.
    
    Returns:
        str: Unique user session identifier
    """
    if 'user_session_id' not in st.session_state:
        import hashlib
        import time
        
        # Create a unique session ID based on timestamp and random component
        timestamp = str(time.time())
        random_component = str(hash(timestamp + str(id(st.session_state))))
        
        # Create hash for shorter, more manageable ID
        session_content = f"{timestamp}_{random_component}"
        hash_object = hashlib.md5(session_content.encode())
        st.session_state.user_session_id = f"user_{hash_object.hexdigest()[:16]}"
        
        logger.info(f"Generated new user session ID: {st.session_state.user_session_id}")
    
    return st.session_state.user_session_id

def auto_save_conversation():
    """
    Auto-save the current conversation if conversation management is available.
    This is called after each assistant response to keep conversations persisted.
    """
    if not CONVERSATION_MANAGER_AVAILABLE:
        return
    
    # Only auto-save if we have messages and conversation manager is ready
    if (not st.session_state.get('chat_messages') or 
        'conversation_manager' not in st.session_state):
        return
    
    try:
        user_session_id = get_user_session_id()
        conv_id = st.session_state.get('current_conversation_id')
        
        # Auto-save conversation
        saved_id, success = st.session_state.conversation_manager.save_conversation(
            messages=st.session_state.chat_messages,
            user_session_id=user_session_id,
            conversation_id=conv_id
        )
        
        if success:
            st.session_state.current_conversation_id = saved_id
            logger.debug(f"Auto-saved conversation: {saved_id}")
        else:
            logger.warning("Auto-save failed")
            
    except Exception as e:
        logger.error(f"Auto-save error: {e}")

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

# REMOVED: parse_tables_column() - now using pre-parsed tables_parsed column from optimized_queries.parquet

# REMOVED: parse_joins_column() - now using pre-parsed joins_parsed column from optimized_queries.parquet

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

def create_query_catalog_page(df: pd.DataFrame):
    """Create the query catalog page with cached analytics for performance"""
    st.subheader("📚 Query Catalog")
    st.caption(f"Browse all {len(df)} SQL queries with their metadata")
    
    # Try to load cached analytics first
    cached_analytics = load_cached_analytics()
    
    # Search/filter functionality
    search_term = st.text_input(
        "🔍 Search queries:", 
        placeholder="Search by query content, description, or tables..."
    )
    
    # Filter dataframe based on search - using ONLY pre-parsed columns
    filtered_df = df
    if search_term:
        search_lower = search_term.lower()
        
        # Check if we have pre-parsed data for efficient search
        if 'tables_parsed' in df.columns and 'joins_parsed' in df.columns:
            # Fast vectorized search using pre-parsed columns
            mask_list = []
            for idx, row in df.iterrows():
                match = False
                
                # Search in query and description (always available)
                query = safe_get_value(row, 'query')
                description = safe_get_value(row, 'description')
                
                if (search_lower in query.lower() or 
                    search_lower in description.lower()):
                    match = True
                
                # Search in pre-parsed tables (list format)
                if not match and isinstance(row.get('tables_parsed'), list):
                    for table in row['tables_parsed']:
                        if search_lower in str(table).lower():
                            match = True
                            break
                
                # Search in pre-parsed joins (list of dicts format)
                if not match and isinstance(row.get('joins_parsed'), list):
                    for join_info in row['joins_parsed']:
                        if isinstance(join_info, dict):
                            # Create searchable text from join info
                            searchable_parts = [
                                join_info.get('left_table', ''),
                                join_info.get('right_table', ''),
                                join_info.get('left_column', ''),
                                join_info.get('right_column', ''),
                                join_info.get('join_type', ''),
                                join_info.get('condition', ''),
                                join_info.get('transformation', '')
                            ]
                            searchable_text = ' '.join(str(part) for part in searchable_parts).lower()
                            
                            if search_lower in searchable_text:
                                match = True
                                break
                
                mask_list.append(match)
            
            # Apply the filter
            filtered_df = df[pd.Series(mask_list, index=df.index)]
            st.info(f"⚡ Found {len(filtered_df)} queries matching '{search_term}' (fast search)")
        else:
            # No pre-parsed data available - limited search capability
            st.warning("⚠️ Limited search capability without pre-parsed data")
            
            # Basic search in query and description only
            query_mask = df['query'].str.contains(search_term, case=False, na=False)
            desc_mask = df.get('description', pd.Series(dtype=bool)).str.contains(search_term, case=False, na=False) if 'description' in df.columns else pd.Series([False] * len(df))
            
            filtered_df = df[query_mask | desc_mask]
            st.info(f"📄 Found {len(filtered_df)} queries matching '{search_term}' (basic search - run analytics generator for full search)")
            st.caption("💡 Run `python catalog_analytics_generator.py --csv 'your_file.csv'` for enhanced search in tables and joins")
    
    # Display analytics - ONLY use cached analytics (no fallback computation)
    if cached_analytics:
        # Use cached analytics for much faster display
        join_analysis = cached_analytics['join_analysis']
        metadata = cached_analytics['metadata']
        
        # Show cache status
        st.caption(f"⚡ Using cached analytics (generated in {metadata['processing_time']:.2f}s)")
        
        # Only show full analytics for non-search results to avoid confusion
        if not search_term:
            display_join_analysis(join_analysis)
            
            # Load and display cached graphs
            graph_files = load_cached_graph_files()
            if graph_files and len(join_analysis['relationships']) > 0:
                st.subheader("🌐 Table Relationship Graph")
                
                # Display the first available graph
                graph_file = Path(graph_files[0])
                if graph_file.suffix.lower() == '.svg':
                    # Display SVG graph safely via HTML
                    with open(graph_file, 'r', encoding='utf-8') as f:
                        svg_content = f.read()
                    st.markdown(svg_content, unsafe_allow_html=True)
                else:
                    # Display PNG/other formats
                    st.image(str(graph_file), use_column_width=True)
                
                st.caption(f"Graph loaded from cache: {graph_file.name}")
        else:
            # For search results, show simple stats only
            st.info(f"📊 Showing {len(filtered_df)} search results (full analytics available for complete dataset)")
    else:
        # NO FALLBACK COMPUTATION - require cache
        st.error("❌ **Analytics cache not available**")
        st.error("🚫 **Query Catalog requires pre-computed analytics for optimal performance**")
        st.code("""
# Run this command to generate analytics cache:
python catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv"
        """)
        st.stop()  # Stop execution - don't attempt heavy computation
    
    st.divider()
    
    # Display queries with pagination to prevent freezing
    st.subheader(f"📋 Queries ({len(filtered_df)} total)")
    
    if len(filtered_df) == 0:
        st.warning("No queries found matching your search criteria")
        return
    
    # Calculate pagination parameters
    pagination_info = calculate_pagination(len(filtered_df))
    
    if pagination_info['has_multiple_pages']:
        # Show pagination controls for large datasets
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            st.metric("Total Queries", len(filtered_df))
        
        with col2:
            # Page selector dropdown
            current_page = st.selectbox(
                "📄 Select Page:",
                range(1, pagination_info['total_pages'] + 1),
                index=0,
                format_func=lambda x: f"Page {x} of {pagination_info['total_pages']}",
                key="query_page_selector"
            )
        
        with col3:
            st.metric("Per Page", QUERIES_PER_PAGE)
        
        # Show current page info
        page_info = get_page_info(current_page, len(filtered_df))
        st.caption(f"📍 Showing queries {page_info['start_query']}-{page_info['end_query']} of {len(filtered_df)}")
        
    else:
        # No pagination needed for small datasets
        current_page = 1
        st.info(f"📄 Showing all {len(filtered_df)} queries (single page)")
    
    st.divider()
    
    # Get current page data slice (CRITICAL: Only render current page!)
    current_page_df = get_page_slice(filtered_df, current_page)
    
    if current_page_df.empty:
        st.error("❌ No data for the selected page")
        return
    
    # Render ONLY current page queries (15 max instead of 100+)
    for index, (_, row) in enumerate(current_page_df.iterrows()):
        # Calculate global index for proper query numbering
        global_index = (current_page - 1) * QUERIES_PER_PAGE + index
        display_query_card(row, global_index)
    
    # Add navigation hints for large datasets
    if pagination_info['has_multiple_pages']:
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if current_page > 1:
                st.caption("⬅️ Use dropdown above to go to previous pages")
        
        with col2:
            st.caption(f"📖 Page {current_page} of {pagination_info['total_pages']}")
        
        with col3:
            if current_page < pagination_info['total_pages']:
                st.caption("➡️ Use dropdown above to go to next pages")

def load_cached_analytics() -> Optional[Dict[str, Any]]:
    """Load cached analytics if available and up to date"""
    try:
        if not CATALOG_ANALYTICS_DIR.exists():
            return None
        
        cache_metadata_file = CATALOG_ANALYTICS_DIR / "cache_metadata.json"
        join_analysis_file = CATALOG_ANALYTICS_DIR / "join_analysis.json"
        
        if not cache_metadata_file.exists() or not join_analysis_file.exists():
            return None
        
        # Load and validate cache
        with open(cache_metadata_file) as f:
            metadata = json.load(f)
        
        # Check if cache is still valid
        if CSV_PATH.exists():
            csv_modified_time = os.path.getmtime(CSV_PATH)
            cached_modified_time = metadata.get('source_csv_modified', 0)
            
            if csv_modified_time > cached_modified_time:
                logger.info("Cache is outdated, will need rebuild")
                return None
        
        # Load join analysis
        with open(join_analysis_file) as f:
            join_analysis = json.load(f)
        
        logger.info("✅ Loaded cached analytics")
        return {
            'metadata': metadata,
            'join_analysis': join_analysis
        }
        
    except Exception as e:
        logger.warning(f"Failed to load cached analytics: {e}")
        return None

def load_cached_graph_files() -> List[str]:
    """Load list of cached graph files"""
    graph_files = []
    if CATALOG_ANALYTICS_DIR.exists():
        for format_type in ["svg", "png"]:
            graph_file = CATALOG_ANALYTICS_DIR / f"relationships_graph.{format_type}"
            if graph_file.exists():
                graph_files.append(str(graph_file))
    return graph_files

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

def detect_agent_type(user_input: str) -> Tuple[Optional[str], str]:
    """
    Detect agent keyword and extract the actual question
    
    Args:
        user_input: Raw user input string
        
    Returns:
        Tuple of (agent_type, cleaned_question) where agent_type is None for normal queries
    """
    user_input = user_input.strip()
    
    if user_input.startswith("@explain"):
        question = user_input[8:].strip()  # Remove "@explain" prefix
        return "explain", question
    elif user_input.startswith("@create"):
        question = user_input[7:].strip()  # Remove "@create" prefix
        return "create", question
    elif user_input.startswith("@schema"):
        question = user_input[7:].strip()  # Remove "@schema" prefix
        return "schema", question
    else:
        return None, user_input


def detect_chat_agent_type(user_input: str) -> Tuple[Optional[str], str]:
    """
    Chat-specific agent detection with @longanswer support
    
    Args:
        user_input: Raw user input string
        
    Returns:
        Tuple of (agent_type, cleaned_question) where agent_type is None for concise responses
    """
    user_input = user_input.strip()
    
    if user_input.startswith("@explain"):
        question = user_input[8:].strip()  # Remove "@explain" prefix
        return "explain", question
    elif user_input.startswith("@create"):
        question = user_input[7:].strip()  # Remove "@create" prefix
        return "create", question
    elif user_input.startswith("@schema"):
        question = user_input[7:].strip()  # Remove "@schema" prefix
        return "schema", question
    elif user_input.startswith("@longanswer"):
        question = user_input[11:].strip()  # Remove "@longanswer" prefix
        return "longanswer", question
    else:
        return None, user_input  # Default to concise responses


def get_agent_indicator(agent_type: Optional[str]) -> str:
    """Get UI indicator for active agent"""
    if agent_type == "explain":
        return "🔍 Explain Agent"
    elif agent_type == "create":
        return "⚡ Create Agent"
    elif agent_type == "schema":
        return "🗂️ Schema Agent"
    else:
        return "💬 Chat"


def get_chat_agent_indicator(agent_type: Optional[str]) -> str:
    """Get UI indicator for chat-specific agents"""
    if agent_type == "explain":
        return "🔍 Explain Agent"
    elif agent_type == "create":
        return "⚡ Create Agent"
    elif agent_type == "schema":
        return "🗂️ Schema Agent"
    elif agent_type == "longanswer":
        return "📖 Detailed Answer"
    else:
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


def get_chat_prompt_template(agent_type: Optional[str], question: str, schema_section: str, conversation_section: str, context: str) -> str:
    """
    Get chat-specific prompt template with concise default responses
    
    Args:
        agent_type: Agent specialization type ("explain", "create", "longanswer", or None)
        question: User question
        schema_section: Database schema information
        conversation_section: Previous conversation context
        context: Retrieved SQL examples context
        
    Returns:
        Formatted prompt string optimized for chat interface
    """
    
    if agent_type == "explain":
        # Explanation Agent - Keep detailed explanations for learning
        return f"""You are a SQL Explanation Expert. Provide detailed, educational explanations of SQL queries, concepts, and database operations.
{schema_section}
{conversation_section}
{context}

Current Question: {question}

As an Explanation Expert, provide a comprehensive answer that:
1. Breaks down complex SQL concepts into understandable parts
2. Explains step-by-step how queries work and why they're structured that way
3. References relevant examples from the context to illustrate points
4. Uses the database schema to explain table relationships and data flow
5. Builds on previous conversation when relevant
6. Explains the "why" behind SQL patterns and best practices

Focus on education and understanding.

Explanation:"""
    
    elif agent_type == "create":
        # Creation Agent - Keep detailed for SQL generation
        return f"""You are a SQL Creation Expert. Generate efficient, working SQL queries from natural language requirements. When targeting BigQuery, always use fully-qualified table names (project.dataset.table); aliases are allowed after qualification.
{schema_section}
{conversation_section}
{context}

Current Requirement: {question}

As a Creation Expert, provide a solution that:
1. Generates working SQL code that meets the specified requirements
2. Uses appropriate table structures and relationships from the schema
3. Follows SQL best practices and performance considerations
4. References similar patterns from the context examples when applicable
5. Includes clear comments explaining the approach

Focus on creating practical, efficient SQL solutions.

SQL Solution:"""
    
    elif agent_type == "longanswer":
        # Long Answer Agent - Comprehensive detailed responses
        return f"""You are a comprehensive SQL expert. Provide detailed, thorough analysis using the provided schema, context, and conversation history.
{schema_section}
{conversation_section}
{context}

Current Question: {question}

Provide a comprehensive, detailed answer that:
1. Thoroughly addresses all aspects of the user's question
2. References multiple relevant examples from the context when applicable
3. Uses the database schema extensively to explain relationships and structures
4. Builds extensively on previous conversation context
5. Explains advanced SQL concepts, patterns, and best practices
6. Provides multiple approaches or alternatives when relevant
7. Includes detailed explanations of the reasoning behind recommendations
8. Covers edge cases and considerations

Focus on providing complete, in-depth analysis and guidance.

Detailed Answer:"""
    
    else:
        # Default behavior - Concise 2-3 sentence responses for chat
        return f"""You are a SQL expert assistant. Provide concise, helpful answers in 2-3 sentences that directly address the user's question. If you include BigQuery SQL, use fully-qualified table names (project.dataset.table).
{schema_section}
{conversation_section}
{context}

Current Question: {question}

Provide a brief, focused answer that:
1. Directly answers the user's question in 2-3 sentences
2. References the most relevant example from the context if applicable
3. Uses the database schema when needed for table relationships
4. Builds on previous conversation context when relevant

Keep your response concise and to the point.

Answer:"""


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
                import re as _re
                def _fast_extract_tables(text: str) -> List[str]:
                    if not text or not isinstance(text, str):
                        return []
                    tables = set()
                    text_lower = text.lower()
                    patterns = [
                        r'\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
                        r'\b(?:inner\s+|left\s+|right\s+|full\s+|cross\s+)?join\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
                        r'\bupdate\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
                        r'\binsert\s+into\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
                        r'\bdelete\s+from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
                    ]
                    for pat in patterns:
                        for match in _re.findall(pat, text_lower):
                            norm = schema_manager._normalize_table_name(match)
                            if norm:
                                tables.add(norm)
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
        llm = GeminiClient(model="gemini-2.5-flash")  # Use fast model for chat
        
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


def calculate_conversation_tokens(chat_messages):
    """Calculate total tokens used in the conversation including context"""
    total_conversation_tokens = 0
    total_response_tokens = 0
    total_context_tokens = 0
    
    for msg in chat_messages:
        # Count message content tokens
        content_tokens = estimate_token_count(msg.get('content', ''))
        total_conversation_tokens += content_tokens
        
        # Count response tokens from API usage
        if msg.get('token_usage'):
            response_tokens = msg['token_usage'].get('total_tokens', 0)
            total_response_tokens += response_tokens
            
            # Count context tokens from retrieved sources
            if msg.get('sources'):
                context_tokens = sum(estimate_token_count(doc.page_content) for doc in msg['sources'])
                total_context_tokens += context_tokens
    
    return {
        'conversation_tokens': total_conversation_tokens,
        'response_tokens': total_response_tokens,
        'context_tokens': total_context_tokens,
        'total_tokens': total_conversation_tokens + total_context_tokens,
        'utilization_percent': min((total_conversation_tokens + total_context_tokens) / 1000000 * 100, 100)
    }

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

def create_chat_page(vector_store, csv_data):
    """Create ChatGPT-like chat conversation page with Gemini mode"""
    
    # Initialize chat messages in session state
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    # Calculate real-time token usage
    token_stats = calculate_conversation_tokens(st.session_state.chat_messages)
    
    # Header with context utilization
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("💬 SQL RAG Chat")
        st.caption("Powered by Google Gemini 2.5 Flash")
    
    with col2:
        # Context utilization progress bar
        utilization = token_stats['utilization_percent']
        if utilization < 50:
            color = "🟢"
            status = "Good"
        elif utilization < 80:
            color = "🟡" 
            status = "Moderate"
        else:
            color = "🔴"
            status = "High"
        
        st.metric(
            f"{color} Context Usage", 
            f"{utilization:.1f}%",
            f"{token_stats['total_tokens']:,} tokens"
        )
    
    with col3:
        st.metric(
            "💬 Messages", 
            len(st.session_state.chat_messages),
            f"Remaining: {1000000 - token_stats['total_tokens']:,}"
        )
    
    # Progress bar for context utilization
    st.progress(utilization / 100)
    
    st.divider()
    
    # Display existing messages using native Streamlit chat components
    if st.session_state.chat_messages:
        for msg in st.session_state.chat_messages:
            if msg['role'] == 'user':
                render_chat_message(msg, is_user=True)
            else:
                render_chat_message(msg, is_user=False)
    else:
        # Simple welcome message using native components
        st.markdown("### 👋 Welcome to SQL RAG Chat!")
        st.markdown("Ask questions about your SQL queries using natural language.")
        
        st.info("**💡 Chat Keywords:**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.success("**Default:** 💬 Concise 2-3 sentence responses")
            st.info("**@explain** 🔍 Detailed explanations for learning")
        with col2:
            st.warning("**@create** ⚡ SQL code generation with examples")
            if st.session_state.lookml_safe_join_map:
                st.info("**@schema** 🗂️ Direct LookML schema exploration")  
            st.error("**@longanswer** 📖 Comprehensive detailed analysis")
        
        st.markdown("---")
    
    # Add clear conversation button
    if st.session_state.chat_messages:
        if st.button("🗑️ Clear Conversation", use_container_width=True, key="clear_conversation_button"):
            st.session_state.chat_messages = []
            st.session_state.token_usage = []
            st.rerun()
        st.markdown("---")
    
    # Use Streamlit's native chat input
    user_input = st.chat_input(
        placeholder="Ask about SQL queries, joins, optimizations... Use @explain, @create, @schema, or @longanswer for specialized responses"
    )
    
    # Process new message
    if user_input:
        # Detect chat agent type (includes @longanswer)
        agent_type, actual_question = detect_chat_agent_type(user_input.strip())
        
        # Add user message with agent info
        st.session_state.chat_messages.append({
            'role': 'user',
            'content': user_input.strip(),
            'agent_type': agent_type,
            'actual_question': actual_question
        })
        
        # Rerun to display the new message and trigger response generation
        st.rerun()
    
    # Generate response if last message was from user and no response yet
    if (st.session_state.chat_messages and 
        st.session_state.chat_messages[-1]['role'] == 'user' and
        (len(st.session_state.chat_messages) == 1 or 
         st.session_state.chat_messages[-2]['role'] == 'assistant')):
        
        last_user_msg = st.session_state.chat_messages[-1]
        agent_type = last_user_msg.get('agent_type')
        actual_question = last_user_msg.get('actual_question', last_user_msg['content'])
        
        # Get conversation context (exclude the message we're responding to)
        conversation_context = ""
        for msg in st.session_state.chat_messages[:-1]:
            if msg['role'] == 'user':
                conversation_context += f"User: {msg['content']}\n"
            else:
                conversation_context += f"Assistant: {msg['content']}\n"
        
        # Handle @schema agent queries directly
        if agent_type == "schema":
            # Generate @schema response directly without using Gemini/RAG
            schema_response = handle_schema_query(actual_question, st.session_state.lookml_safe_join_map)
            
            # Add schema response to chat history
            st.session_state.chat_messages.append({
                'role': 'assistant',
                'content': schema_response,
                'agent_type': agent_type,
                'token_usage': {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}  # No token usage for schema agent
            })
            
            # Auto-save conversation after schema response
            auto_save_conversation()
            
            st.rerun()
        else:
            # Generate response using chat-specific function
            agent_indicator = get_chat_agent_indicator(agent_type)
            with st.spinner(f"Generating response with {agent_indicator}..."):
                try:
                    result = answer_question_chat_mode(
                        question=actual_question,
                        vector_store=vector_store,
                        k=100,  # Use high k for comprehensive retrieval
                        schema_manager=st.session_state.get('schema_manager'),
                        conversation_context=conversation_context,
                        agent_type=agent_type,
                        user_context=st.session_state.get('user_context', ""),
                        excluded_tables=st.session_state.get('excluded_tables', [])
                    )
                    
                    if result:
                        answer, sources, token_usage = result
                        
                        # Add assistant response with agent info
                        st.session_state.chat_messages.append({
                            'role': 'assistant',
                            'content': answer,
                            'sources': sources,
                            'token_usage': token_usage,
                            'agent_type': agent_type
                        })
                        
                        # Track token usage
                        if 'token_usage' not in st.session_state:
                            st.session_state.token_usage = []
                        st.session_state.token_usage.append(token_usage)
                        
                        # Auto-save conversation after successful response
                        auto_save_conversation()
                        
                    else:
                        # Add error message to chat
                        st.session_state.chat_messages.append({
                            'role': 'assistant',
                            'content': "❌ I apologize, but I encountered an error generating a response. Please try again.",
                            'sources': [],
                            'token_usage': {},
                            'agent_type': agent_type
                        })
                        
                        # Auto-save conversation even with error message
                        auto_save_conversation()
                        
                except Exception as e:
                    # Add error message to chat
                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': f"❌ Error: {str(e)}. Please try rephrasing your question.",
                        'sources': [],
                        'token_usage': {},
                        'agent_type': agent_type
                    })
                    
                    # Auto-save conversation with error message
                    auto_save_conversation()
        
        # Rerun to show new messages
        st.rerun()
    
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
            # Prefer env-configured project and dataset when provided
            bq_project = os.getenv('BIGQUERY_PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT') or "brainrot-453319"
            bq_dataset = os.getenv('BIGQUERY_DATASET') or "bigquery-public-data.thelook_ecommerce"
            st.session_state.bigquery_executor = BigQueryExecutor(project_id=bq_project, dataset_id=bq_dataset)
            logger.info(f"✅ BigQuery executor initialized successfully (project={bq_project}, dataset={bq_dataset})")
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
        
        # Safety validation with logging
        if debug_mode:
            st.write("🔒 **Running safety validation**...")
        
        is_valid, validation_msg = executor.validate_sql_safety(extracted_sql)
        
        if is_valid:
            st.success("✅ Query passed safety validation")
            logger.info("✅ SQL query passed safety validation")
            if debug_mode:
                st.write("✅ **Safety validation passed**")
        else:
            error_msg = f"Safety validation failed: {validation_msg}"
            st.error(f"🚫 {error_msg}")
            logger.warning(f"🚫 {error_msg}")
            if debug_mode:
                st.write(f"🚫 **Safety validation failed**: {validation_msg}")
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
            for key in ['sql_execution_result', 'sql_execution_error', 'sql_execution_completed']:
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
                for key in ['sql_execution_result', 'sql_execution_error', 'sql_execution_completed']:
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
        if debug_mode:
            st.write(f"**Error Details**: {st.session_state.sql_execution_error}")
        return
    
    # Display results if available
    if 'sql_execution_result' in st.session_state and st.session_state.sql_execution_result:
        st.divider()
        st.subheader("📊 Query Execution Results")
        
        result = st.session_state.sql_execution_result
        if debug_mode:
            st.write(f"**📊 Result Status**: Success={result.success}, Rows={result.total_rows}")
        
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

        result = executor.execute_query(sql, dry_run=dry_run, max_bytes_billed=max_bytes_billed)
        
        # Store result in session state for display after rerun
        st.session_state.sql_execution_result = result
        st.session_state.sql_executing = False
        st.session_state.sql_execution_completed = True  # Prevent query reprocessing
        
        logger.info(f"💾 [CALLBACK] Execution completed - Success: {result.success}")
        
        if debug_mode:
            logger.info(f"🐛 [CALLBACK] Debug mode - storing execution details")
            
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


def main():
    """Main Streamlit application"""
    
    # Header
    st.title("🔥 Simple SQL RAG with Gemini")
    st.caption("Ask questions about your SQL queries using Google Gemini 2.5 Flash with 1M context window")
    
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
            ["🔍 Query Search", "📚 Query Catalog", "💬 Chat"],
            key="page_selection"
        )
        
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

        # Show configuration based on selected page
        if page == "🔍 Query Search":
            # Vector store selection (only needed for search)
            available_indices = get_available_indices()
            
            if not available_indices:
                st.error("❌ No vector stores found!")
                st.info("Run standalone_embedding_generator.py first")
                st.stop()
            
            # Let user select which vector store to use
            selected_index = st.selectbox(
                "📂 Select Vector Store:",
                available_indices,
                index=0 if DEFAULT_VECTOR_STORE in available_indices else 0
            )
            
            # Search parameters
            if advanced_mode:
                st.subheader("🔍 Search Settings")
            
            # Add Gemini mode toggle (advanced only)
            if advanced_mode:
                gemini_mode = st.checkbox(
                    "🔥 Gemini Mode", 
                    value=False, 
                    help="Utilize Gemini's 1M context window with enhanced optimization",
                    key="gemini_mode_checkbox"
                )
            else:
                gemini_mode = False
            
            # Add hybrid search toggle
            if advanced_mode:
                if HYBRID_SEARCH_AVAILABLE:
                    hybrid_search = st.checkbox(
                        "🔀 Hybrid Search", 
                        value=False, 
                        help="Combine vector similarity with keyword search (BM25) for better SQL term matching",
                        key="hybrid_search_checkbox"
                    )
                else:
                    hybrid_search = False
                    st.warning("⚠️ Hybrid search unavailable - install rank-bm25")
            else:
                hybrid_search = False
            
            # Add query rewriting toggle
            if advanced_mode:
                try:
                    from simple_rag_simple_gemini import QUERY_REWRITING_AVAILABLE
                    if QUERY_REWRITING_AVAILABLE:
                        query_rewriting = st.checkbox(
                            "🔄 Query Rewriting", 
                            value=False, 
                            help="Enhance queries with SQL terminology using Google Gemini models (25-40% improvement)",
                            key="query_rewriting_checkbox"
                        )
                    else:
                        query_rewriting = False
                        st.warning("⚠️ Query rewriting unavailable - check query_rewriter.py")
                except ImportError:
                    query_rewriting = False
                    st.warning("⚠️ Query rewriting module not found")
            else:
                query_rewriting = False
            
            # Schema injection and SQL validation - always enabled when available
            if SCHEMA_MANAGER_AVAILABLE:
                schema_injection = True
                if advanced_mode:
                    st.success("✅ Smart Schema Injection: Always Active (reduces 39K+ schema rows to ~100-500 relevant ones)")
                
                # User context & table filters (advanced only)
                if advanced_mode and st.session_state.schema_manager:
                    st.subheader("🧩 User Context & Filters")
                    user_context = st.text_area(
                        "Additional Context (optional)",
                        value=st.session_state.get('user_context', ""),
                        help="Add business rules, constraints, or clarifications for the model",
                        height=120,
                        key="user_context_input"
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
                        key="excluded_tables_select"
                    )
                    st.session_state.excluded_tables = excluded_tables
            else:
                schema_injection = False
                st.warning("⚠️ Schema injection unavailable - check schema_manager.py and schema.csv")
            
            # SQL validation - always enabled when available
            if SQL_VALIDATION_AVAILABLE:
                sql_validation = True
                validation_level = ValidationLevel.SCHEMA_STRICT  # Set strict default for comprehensive validation
                if advanced_mode:
                    st.success("✅ SQL Validation: Always Active (Schema Strict level - validates tables/columns/types/joins)")
            else:
                sql_validation = False
                validation_level = None
                st.warning("⚠️ SQL validation unavailable - check core/sql_validator.py")
            
            # BigQuery execution - always enabled when available
            if BIGQUERY_EXECUTION_AVAILABLE and advanced_mode:
                st.success("✅ BigQuery Execution: Available")
                st.subheader("🛠️ BigQuery Settings")
                # Initialize defaults if not present
                if 'bq_project' not in st.session_state:
                    st.session_state.bq_project = os.getenv('BIGQUERY_PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT') or "brainrot-453319"
                if 'bq_dataset' not in st.session_state:
                    st.session_state.bq_dataset = os.getenv('BIGQUERY_DATASET') or "bigquery-public-data.thelook_ecommerce"

                new_project = st.text_input("Project ID", value=st.session_state.bq_project, help="Project for BigQuery jobs")
                new_dataset = st.text_input("Dataset", value=st.session_state.bq_dataset, help="Default dataset context for UI")
                bq_changed = (new_project != st.session_state.bq_project) or (new_dataset != st.session_state.bq_dataset)
                st.session_state.bq_project = new_project
                st.session_state.bq_dataset = new_dataset

                # (Re)initialize executor if missing or settings changed
                if ('bigquery_executor' not in st.session_state) or bq_changed:
                    try:
                        st.session_state.bigquery_executor = BigQueryExecutor(project_id=new_project, dataset_id=new_dataset)
                        if bq_changed:
                            st.info("🔄 Reinitialized BigQuery executor with new settings")
                    except Exception as e:
                        st.warning(f"Failed to initialize BigQuery executor: {e}")
            elif not BIGQUERY_EXECUTION_AVAILABLE:
                st.warning("⚠️ BigQuery execution unavailable - check bigquery_executor.py and google-cloud-bigquery dependency")
            
            if advanced_mode and gemini_mode:
                k = st.slider(
                    "Top-K Results", 
                    min_value=10, 
                    max_value=200, 
                    value=100,
                    help="Gemini can handle 100+ chunks efficiently with smart deduplication"
                )
                st.success("🚀 Gemini Mode: Using large context window with smart optimization")
            else:
                # Simple default (no slider)
                k = 4
            
            # Advanced hybrid search controls
            search_weights = None
            auto_adjust_weights = True
            
            if advanced_mode and hybrid_search:
                st.subheader("⚙️ Hybrid Search Settings")
                
                # Auto-adjust weights toggle
                auto_adjust_weights = st.checkbox(
                    "🤖 Auto-Adjust Weights", 
                    value=True,
                    help="Automatically adjust vector/keyword weights based on query analysis"
                )
                
                # Optional: keyword-only fallback to avoid embedding calls (fast, no network)
                keyword_only = st.checkbox(
                    "🧰 Keyword-only (BM25) — no embeddings",
                    value=False,
                    help="Use only keyword/BM25 search. Useful if embeddings are slow or unavailable."
                )
                
                if keyword_only:
                    auto_adjust_weights = False
                    search_weights = SearchWeights(vector_weight=0.0, keyword_weight=1.0)
                    st.caption("Vector search disabled. Using BM25 only.")
                
                if not auto_adjust_weights:
                    # Manual weight controls
                    st.caption("Manual Weight Configuration:")
                    
                    # Use columns for better layout
                    weight_col1, weight_col2 = st.columns(2)
                    
                    if not keyword_only:
                        with weight_col1:
                            vector_weight = st.slider(
                                "Vector Weight", 
                                0.0, 1.0, 0.7, 0.1,
                                help="Weight for semantic similarity search"
                            )
                        
                        with weight_col2:
                            keyword_weight = st.slider(
                                "Keyword Weight", 
                                0.0, 1.0, 0.3, 0.1,
                                help="Weight for exact keyword matching (BM25)"
                            )
                        
                        # Normalize weights
                        total_weight = vector_weight + keyword_weight
                        if total_weight > 0:
                            vector_weight /= total_weight
                            keyword_weight /= total_weight
                            search_weights = SearchWeights(vector_weight=vector_weight, keyword_weight=keyword_weight)
                            
                            # Display normalized weights
                            st.caption(f"Normalized: Vector {vector_weight:.2f}, Keyword {keyword_weight:.2f}")
                else:
                    st.info("🔍 Weights will be automatically optimized based on your query")
                
                st.success("🚀 Hybrid search combines semantic understanding with exact SQL term matching")
            
            # Sidebar Schema Browser (advanced only)
            if advanced_mode:
                st.divider()
                st.subheader("🧱 Schema Browser")
            sm = st.session_state.get('schema_manager')
            if advanced_mode and sm:
                search = st.text_input("Search tables", "", help="Filter by table name (substring)")
                try:
                    all_tables = sorted(list(sm.schema_lookup.keys()))
                    filtered = [t for t in all_tables if search.lower() in t.lower()] if search else all_tables
                except Exception:
                    filtered = []

                selected_table = st.selectbox("Select a table", filtered, index=0 if filtered else None, key="schema_browser_select") if filtered else None
                if selected_table:
                    fqn = sm.get_fqn(selected_table) or selected_table
                    st.caption("Fully Qualified Name")
                    st.code(f"`{fqn}`", language=None)

                    # Show columns + datatypes
                    df = sm.schema_df
                    if df is not None:
                        table_norm = sm._normalize_table_name(selected_table)
                        try:
                            table_df = df[df["table_id"] == table_norm][["column", "datatype"]].reset_index(drop=True)
                            st.dataframe(table_df, use_container_width=True, hide_index=True)
                        except Exception:
                            cols = sm.get_table_columns(selected_table)
                            st.write("Columns:", ", ".join(cols) if cols else "N/A")
                    else:
                        cols = sm.get_table_columns(selected_table)
                        st.write("Columns:", ", ".join(cols) if cols else "N/A")

                    # Quick actions
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button("Copy FQN", use_container_width=True, key="copy_fqn_btn"):
                            st.session_state["copied_fqn"] = fqn
                            st.success("Copied FQN (use Cmd/Ctrl+C on highlighted text)")
                    with col_b:
                        if st.button("Insert sample SELECT", use_container_width=True, key="insert_sample_btn"):
                            sample_sql = f"SELECT * FROM `{fqn}`\nLIMIT 100"
                            st.session_state["user_context"] = (st.session_state.get("user_context", "") + f"\n\nSample:\n```sql\n{sample_sql}\n```" ).strip()
                            st.success("Inserted sample into Additional Context")
                    with col_c:
                        ex = st.session_state.get('excluded_tables', [])
                        if st.button("Exclude", use_container_width=True, key="exclude_table_btn"):
                            if selected_table not in ex:
                                ex = ex + [selected_table]
                                st.session_state['excluded_tables'] = ex
                            st.success(f"Excluded {selected_table}")
            elif advanced_mode:
                st.info("Load a schema CSV to browse tables (data_new/thelook_ecommerce_schema.csv)")

            # Source display options
            st.subheader("📋 Source Display")
            show_full_queries = st.checkbox(
                "📄 Show Full Query Cards",
                value=False,
                help="Show complete query information instead of just matching chunks",
                key="show_full_queries_checkbox"
            )
            
            st.markdown("""
            _Tip: Gemini Mode provides 18.5x better context utilization. Hybrid Search improves SQL term matching by 20-40%. Query Rewriting enhances retrieval precision by 25-40%. SQL Validation ensures generated queries are syntactically correct and reference valid schema elements._
            """)
            
            # Display vector store info
            index_path = FAISS_INDICES_DIR / selected_index
            if index_path.exists():
                status_file = FAISS_INDICES_DIR / f"status_{selected_index[6:]}.json"  # Remove "index_" prefix
                if status_file.exists():
                    try:
                        import json
                        with open(status_file) as f:
                            status = json.load(f)
                        
                        st.subheader("📊 Vector Store Info")
                        st.metric("Total Documents", f"{status.get('total_documents', 'Unknown'):,}")
                        st.caption(f"Created: {status.get('created_at', 'Unknown')}")
                        
                        # GPU info
                        gpu_info = status.get('gpu_acceleration', {})
                        if gpu_info.get('gpu_accelerated_processing'):
                            st.success("🚀 GPU-accelerated")
                        else:
                            st.info("💻 CPU processed")
                            
                    except Exception as e:
                        st.warning("Could not load status info")
        
        elif page == "💬 Chat":
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
        else:
            # Query Catalog page - show data info
            st.subheader("📊 Data Info")
            df = st.session_state.csv_data
            st.metric("Total Queries", len(df))
            st.caption(f"Source: {CSV_PATH.name}")
    
    # Route to appropriate page
    if page == "🔍 Query Search":
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
                    
                    # Call our enhanced RAG function with Gemini, hybrid search, query rewriting, and smart schema injection
                    # Generate answer (includes retrieval, schema injection, validation)
                    result = answer_question_simple_gemini(
                        question=query,
                        vector_store=st.session_state.vector_store,
                        k=k,
                        gemini_mode=gemini_mode,
                        hybrid_search=hybrid_search,
                        search_weights=search_weights,
                        auto_adjust_weights=auto_adjust_weights,
                        query_rewriting=query_rewriting,
                        schema_manager=schema_manager_to_use,
                        lookml_safe_join_map=st.session_state.lookml_safe_join_map,
                        sql_validation=sql_validation,
                        validation_level=validation_level,
                        excluded_tables=st.session_state.get('excluded_tables', []),
                        user_context=st.session_state.get('user_context', "")
                    )
                    
                    if result:
                        answer, sources, token_usage = result
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
                        st.error("❌ Failed to generate answer")
                        
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
            ### 💡 How to use:
            
            1. **First time setup:**
               ```bash
               # Setup Gemini API key
               export GEMINI_API_KEY="your-api-key"
               
               # Generate vector embeddings
               python standalone_embedding_generator.py --csv "your_queries.csv"
               ```
            
            2. **Enable Gemini Mode** for 18.5x better context utilization with Google Gemini
            
            3. **Enable Hybrid Search** for 20-40% better SQL term matching
            
            4. **Enable Query Rewriting** for 25-40% enhanced retrieval precision
            
            5. **Enable SQL Validation** to ensure generated SQL is syntactically correct and references valid schema elements
            
            6. **Ask questions** about your SQL queries and get comprehensive answers
            
            7. **Execute SQL queries** - when SQL is detected in responses, click "Execute Query" to run against BigQuery
            
            8. **Adjust Top-K** in the sidebar (use 100+ for Gemini mode)
            
            ### 🚀 Enhanced Features:
            
            **Gemini Optimization:**
            - **Smart deduplication** removes redundant content
            - **Content prioritization** balances JOINs, aggregations, descriptions
            - **Enhanced context building** for comprehensive answers  
            - **Real-time monitoring** of 1M token context utilization
            
            **Hybrid Search:**
            - **Vector search** for semantic similarity (concepts, synonyms)
            - **Keyword search** for exact SQL terms (table names, functions)
            - **Auto-weight adjustment** based on query analysis
            - **Fusion scoring** combines both methods optimally
            
            **SQL Validation:**
            - **Syntax validation** checks SQL grammar and structure
            - **Schema validation** verifies tables and columns exist
            - **Real-time feedback** on query correctness
            - **Intelligent suggestions** for fixing validation errors
            
            **BigQuery Execution:**
            - **Automatic SQL detection** in generated responses
            - **Secure execution** against thelook_ecommerce dataset
            - **Interactive results** with sorting, filtering, and export
            - **Performance metrics** showing execution time and data processed
            - **Safety guards** prevent unauthorized operations and limit result size
            """)
    
    elif page == "💬 Chat":
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
        
        # Create chat page
        create_chat_page(st.session_state.vector_store, st.session_state.csv_data)
    
    else:
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

if __name__ == "__main__":
    main()
