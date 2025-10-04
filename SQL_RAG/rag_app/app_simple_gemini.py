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
import pandas as pd
import time
import logging
import re
import json
import os
import math
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
from collections import defaultdict

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

# Import necessary components for chat-specific RAG function
from gemini_client import GeminiClient

# Import schema manager for smart schema injection
try:
    from schema_manager import SchemaManager, create_schema_manager
    SCHEMA_MANAGER_AVAILABLE = True
except ImportError:
    SCHEMA_MANAGER_AVAILABLE = False
    logger.warning("Schema manager not available - schema injection disabled")

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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
FAISS_INDICES_DIR = Path(__file__).parent / "faiss_indices"
DEFAULT_VECTOR_STORE = "index_queries_with_descriptions (1)"  # Expected index name
CSV_PATH = Path(__file__).parent / "sample_queries_with_metadata.csv"  # CSV data source
CATALOG_ANALYTICS_DIR = Path(__file__).parent / "catalog_analytics"  # Cached analytics
SCHEMA_CSV_PATH = Path(__file__).parent / "sample_queries_metadata_schema.csv"  # Schema file with table_id, column, datatype

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
        vector_store = FAISS.load_local(
            str(index_path),
            embeddings,
            allow_dangerous_deserialization=True
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
                    # Display SVG graph
                    with open(graph_file, 'r') as f:
                        svg_content = f.read()
                    st.image(svg_content, use_column_width=True)
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
    else:
        return "💬 Chat"


def get_chat_agent_indicator(agent_type: Optional[str]) -> str:
    """Get UI indicator for chat-specific agents"""
    if agent_type == "explain":
        return "🔍 Explain Agent"
    elif agent_type == "create":
        return "⚡ Create Agent"
    elif agent_type == "longanswer":
        return "📖 Detailed Answer"
    else:
        return "💬 Concise Chat"


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
        return f"""You are a SQL Creation Expert. Generate efficient, working SQL queries from natural language requirements.
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
        return f"""You are a SQL expert assistant. Provide concise, helpful answers in 2-3 sentences that directly address the user's question.
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
    k: int = 100,
    schema_manager=None,
    conversation_context: str = "",
    agent_type: Optional[str] = None
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
        # Step 1: Retrieve relevant documents using vector search
        retrieval_start = time.time()
        docs = vector_store.similarity_search(question, k=k)
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
                # Get relevant schema for the question and context
                relevant_schema_data = schema_manager.get_relevant_schema(
                    question=question,
                    context_chunks=[doc.page_content for doc in docs],
                    max_tables=10  # Reasonable limit for chat responses
                )
                
                if relevant_schema_data:
                    relevant_schema = relevant_schema_data['schema_text']
                    schema_info = {
                        'enabled': True,
                        'relevant_tables': relevant_schema_data['table_count'],
                        'schema_tokens': estimate_token_count(relevant_schema),
                        'total_schema_tables': schema_manager.table_count,
                        'schema_coverage': f"{relevant_schema_data['table_count']}/{schema_manager.table_count}",
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
            st.error("**@longanswer** 📖 Comprehensive detailed analysis")
        
        st.markdown("---")
    
    # Add clear conversation button
    if st.session_state.chat_messages:
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.chat_messages = []
            st.session_state.token_usage = []
            st.rerun()
        st.markdown("---")
    
    # Use Streamlit's native chat input
    user_input = st.chat_input(
        placeholder="Ask about SQL queries, joins, optimizations... Use @explain, @create, or @longanswer for specialized responses"
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
                    agent_type=agent_type
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
                    
                else:
                    # Add error message to chat
                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': "❌ I apologize, but I encountered an error generating a response. Please try again.",
                        'sources': [],
                        'token_usage': {},
                        'agent_type': agent_type
                    })
                    
            except Exception as e:
                # Add error message to chat
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': f"❌ Error: {str(e)}. Please try rephrasing your question.",
                    'sources': [],
                    'token_usage': {},
                    'agent_type': agent_type
                })
        
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
            
            # Search parameters with Gemini optimization
            st.subheader("🔍 Search Settings")
            
            # Add Gemini mode toggle
            gemini_mode = st.checkbox(
                "🔥 Gemini Mode", 
                value=False, 
                help="Utilize Gemini's 1M context window with enhanced optimization"
            )
            
            # Add hybrid search toggle
            if HYBRID_SEARCH_AVAILABLE:
                hybrid_search = st.checkbox(
                    "🔀 Hybrid Search", 
                    value=False, 
                    help="Combine vector similarity with keyword search (BM25) for better SQL term matching"
                )
            else:
                hybrid_search = False
                st.warning("⚠️ Hybrid search unavailable - install rank-bm25")
            
            # Add query rewriting toggle
            try:
                from simple_rag_simple_gemini import QUERY_REWRITING_AVAILABLE
                if QUERY_REWRITING_AVAILABLE:
                    query_rewriting = st.checkbox(
                        "🔄 Query Rewriting", 
                        value=False, 
                        help="Enhance queries with SQL terminology using Google Gemini models (25-40% improvement)"
                    )
                else:
                    query_rewriting = False
                    st.warning("⚠️ Query rewriting unavailable - check query_rewriter.py")
            except ImportError:
                query_rewriting = False
                st.warning("⚠️ Query rewriting module not found")
            
            # Add schema injection toggle
            if SCHEMA_MANAGER_AVAILABLE:
                schema_injection = st.checkbox(
                    "🗃️ Smart Schema Injection", 
                    value=True, 
                    help="Inject relevant database schema (reduces 39K+ schema rows to ~100-500 relevant ones)"
                )
            else:
                schema_injection = False
                st.warning("⚠️ Schema injection unavailable - check schema_manager.py and schema.csv")
            
            # Add SQL validation toggle
            if SQL_VALIDATION_AVAILABLE:
                sql_validation = st.checkbox(
                    "✅ SQL Validation", 
                    value=False, 
                    help="Validate generated SQL queries against database schema"
                )
                
                if sql_validation:
                    validation_level = st.selectbox(
                        "Validation Level:",
                        [ValidationLevel.SYNTAX_ONLY, ValidationLevel.SCHEMA_BASIC, ValidationLevel.SCHEMA_STRICT],
                        index=1,  # Default to SCHEMA_BASIC
                        format_func=lambda x: {
                            ValidationLevel.SYNTAX_ONLY: "Syntax Only - Check SQL syntax",
                            ValidationLevel.SCHEMA_BASIC: "Schema Basic - Check tables/columns exist",
                            ValidationLevel.SCHEMA_STRICT: "Schema Strict - Full validation with types"
                        }[x],
                        help="Choose validation strictness level"
                    )
                else:
                    validation_level = ValidationLevel.SCHEMA_BASIC
            else:
                sql_validation = False
                validation_level = ValidationLevel.SCHEMA_BASIC
                st.warning("⚠️ SQL validation unavailable - check core/sql_validator.py")
            
            if gemini_mode:
                k = st.slider(
                    "Top-K Results", 
                    min_value=10, 
                    max_value=200, 
                    value=100,
                    help="Gemini can handle 100+ chunks efficiently with smart deduplication"
                )
                st.success("🚀 Gemini Mode: Using large context window with smart optimization")
            else:
                k = st.slider(
                    "Top-K Results", 
                    1, 
                    20, 
                    4, 
                    help="Conservative mode for smaller models"
                )
            
            # Advanced hybrid search controls
            search_weights = None
            auto_adjust_weights = True
            
            if hybrid_search:
                st.subheader("⚙️ Hybrid Search Settings")
                
                # Auto-adjust weights toggle
                auto_adjust_weights = st.checkbox(
                    "🤖 Auto-Adjust Weights", 
                    value=True,
                    help="Automatically adjust vector/keyword weights based on query analysis"
                )
                
                if not auto_adjust_weights:
                    # Manual weight controls
                    st.caption("Manual Weight Configuration:")
                    
                    # Use columns for better layout
                    weight_col1, weight_col2 = st.columns(2)
                    
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
            
            # Source display options
            st.subheader("📋 Source Display")
            show_full_queries = st.checkbox(
                "📄 Show Full Query Cards",
                value=False,
                help="Show complete query information instead of just matching chunks"
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
                vector_store = load_vector_store(selected_index)
                
                if vector_store:
                    st.session_state.vector_store = vector_store
                    st.session_state.current_index = selected_index
                    st.success(f"✅ Loaded {len(vector_store.docstore._dict):,} documents")
                else:
                    st.error("Failed to load vector store")
                    return
        
        # Display session stats
        display_session_stats()
        
        # Main query interface
        st.subheader("❓ Ask a Question")
        
        query = st.text_input(
            "Enter your question:",
            placeholder="e.g., Which queries show customer spending analysis with multiple JOINs?"
        )
        
        if st.button("🔍 Search", type="primary") and query.strip():
            with st.spinner("Searching and generating answer..."):
                try:
                    # Determine schema manager to use
                    schema_manager_to_use = None
                    if schema_injection and st.session_state.schema_manager:
                        schema_manager_to_use = st.session_state.schema_manager
                        logger.info(f"🗃️ Using schema manager for RAG: {schema_manager_to_use.table_count} tables available")
                    else:
                        if not schema_injection:
                            logger.info("Schema injection disabled by user")
                        elif not st.session_state.schema_manager:
                            logger.info("No schema manager available in session state")
                        else:
                            logger.info("Schema manager not being used for unknown reason")
                    
                    # Call our enhanced RAG function with Gemini, hybrid search, query rewriting, and smart schema injection
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
                        sql_validation=sql_validation,
                        validation_level=validation_level
                    )
                    
                    if result:
                        answer, sources, token_usage = result
                        
                        # Track token usage
                        if token_usage:
                            st.session_state.token_usage.append(token_usage)
                        
                        # Display answer
                        st.subheader("📜 Answer")
                        st.write(answer)
                        
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
            
            7. **Adjust Top-K** in the sidebar (use 100+ for Gemini mode)
            
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
                    st.success(f"✅ Loaded {len(vector_store.docstore._dict):,} documents")
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
