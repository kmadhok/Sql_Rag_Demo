#!/usr/bin/env python3
"""
Query catalog functionality for SQL RAG Streamlit application.
Extracted from app_simple_gemini.py for better modularity.
"""

import streamlit as st
import pandas as pd
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from .config import CATALOG_ANALYTICS_DIR, QUERIES_PER_PAGE, MAX_PAGES_TO_SHOW
from .utils import safe_get_value, calculate_pagination, get_page_slice, get_page_info
from .data_loader import load_join_analysis, load_table_relationships

# Configure logging
logger = logging.getLogger(__name__)


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
    else:
        st.info("No join relationships found in the data")


def load_cached_analytics() -> dict:
    """Load cached analytics from JSON files"""
    if not CATALOG_ANALYTICS_DIR.exists():
        return {}
    
    try:
        # Load join analysis
        join_analysis = load_join_analysis()
        
        # Load metadata if available
        metadata_path = CATALOG_ANALYTICS_DIR / "analytics_metadata.json"
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        
        if join_analysis:
            return {
                'join_analysis': join_analysis,
                'metadata': metadata
            }
        return {}
        
    except Exception as e:
        logger.warning(f"Failed to load cached analytics: {e}")
        return {}


def load_cached_graph_files() -> List[str]:
    """Load list of cached graph files"""
    if not CATALOG_ANALYTICS_DIR.exists():
        return []
    
    graph_files = []
    for ext in ['.svg', '.png', '.pdf']:
        for graph_file in CATALOG_ANALYTICS_DIR.glob(f"*graph*{ext}"):
            graph_files.append(str(graph_file))
    
    return sorted(graph_files)


def search_queries(df: pd.DataFrame, search_term: str) -> pd.DataFrame:
    """Search queries using pre-parsed data for optimal performance"""
    if not search_term:
        return df
    
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
        return filtered_df
    else:
        # No pre-parsed data available - limited search capability
        # Basic search in query and description only
        query_mask = df['query'].str.contains(search_term, case=False, na=False)
        desc_mask = df.get('description', pd.Series(dtype=bool)).str.contains(search_term, case=False, na=False) if 'description' in df.columns else pd.Series([False] * len(df))
        
        filtered_df = df[query_mask | desc_mask]
        return filtered_df


def display_pagination_controls(filtered_df: pd.DataFrame) -> int:
    """Display pagination controls and return selected page number"""
    pagination = calculate_pagination(len(filtered_df))
    
    if not pagination['has_multiple_pages']:
        return 1
    
    # Create pagination controls
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.write("")  # Spacer
    
    with col2:
        # Show page selection dropdown or navigation
        if pagination['total_pages'] <= MAX_PAGES_TO_SHOW:
            # Show dropdown for reasonable number of pages
            page_options = list(range(1, pagination['total_pages'] + 1))
            selected_page = st.selectbox(
                f"Page (showing {pagination['page_size']} queries per page):",
                page_options,
                index=0,
                format_func=lambda x: f"Page {x} of {pagination['total_pages']}"
            )
        else:
            # Show number input for large number of pages
            selected_page = st.number_input(
                f"Page (1-{pagination['total_pages']}):",
                min_value=1,
                max_value=pagination['total_pages'],
                value=1,
                step=1
            )
    
    with col3:
        st.write("")  # Spacer
    
    return selected_page


def display_queries_for_page(filtered_df: pd.DataFrame, page_num: int):
    """Display queries for the selected page"""
    page_df = get_page_slice(filtered_df, page_num)
    
    if page_df.empty:
        st.warning("No queries found for this page.")
        return
    
    # Show page info
    page_info = get_page_info(page_num, len(filtered_df))
    st.caption(f"Showing queries {page_info['start_query']}-{page_info['end_query']} of {len(filtered_df)}")
    
    # Display each query in the page
    for idx, (_, row) in enumerate(page_df.iterrows()):
        # Calculate global index for proper numbering
        global_idx = (page_num - 1) * QUERIES_PER_PAGE + idx
        display_query_card(row, global_idx)


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
    
    # Filter dataframe based on search
    filtered_df = search_queries(df, search_term)
    
    if search_term:
        if 'tables_parsed' in df.columns and 'joins_parsed' in df.columns:
            st.info(f"⚡ Found {len(filtered_df)} queries matching '{search_term}' (fast search)")
        else:
            st.warning("⚠️ Limited search capability without pre-parsed data")
            st.info(f"📄 Found {len(filtered_df)} queries matching '{search_term}' (basic search - run analytics generator for full search)")
            st.caption("💡 Run `python catalog_analytics_generator.py --csv 'your_file.csv'` for enhanced search in tables and joins")
    
    # Display analytics - ONLY use cached analytics (no fallback computation)
    if cached_analytics:
        # Use cached analytics for much faster display
        join_analysis = cached_analytics['join_analysis']
        metadata = cached_analytics['metadata']
        
        # Show cache status
        if metadata:
            st.caption(f"⚡ Using cached analytics (generated in {metadata.get('processing_time', 0):.2f}s)")
        
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
    
    if filtered_df.empty:
        st.info("No queries match your search criteria.")
        return
    
    # Pagination controls
    selected_page = display_pagination_controls(filtered_df)
    
    # Display queries for selected page
    display_queries_for_page(filtered_df, selected_page)