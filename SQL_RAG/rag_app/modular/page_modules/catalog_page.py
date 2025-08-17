#!/usr/bin/env python3
"""
Query Catalog Page for Modular SQL RAG application.
Handles browsing and searching through the query catalog with analytics.
"""

import streamlit as st
import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from modular.config import PAGE_NAMES, QUERIES_PER_PAGE, CATALOG_ANALYTICS_DIR
from modular.session_manager import session_manager
from modular.data_loader import load_join_analysis, load_table_relationships
from modular.utils import (
    safe_get_value, calculate_pagination, get_page_slice, get_page_info,
    parse_json_safely
)

# Configure logging
logger = logging.getLogger(__name__)


class CatalogPage:
    """Query Catalog page implementation"""
    
    def __init__(self):
        self.page_title = PAGE_NAMES['catalog']
    
    def load_cached_analytics(self) -> Optional[Dict[str, Any]]:
        """Load cached analytics if available"""
        try:
            if not CATALOG_ANALYTICS_DIR.exists():
                return None
            
            # Load join analysis and table relationships
            join_analysis = load_join_analysis()
            table_relationships = load_table_relationships()
            
            if not join_analysis:
                return None
            
            logger.info("✅ Loaded cached analytics")
            return {
                'join_analysis': join_analysis,
                'table_relationships': table_relationships
            }
            
        except Exception as e:
            logger.warning(f"Failed to load cached analytics: {e}")
            return None
    
    def load_cached_graph_files(self) -> List[str]:
        """Load list of cached graph files"""
        graph_files = []
        if CATALOG_ANALYTICS_DIR.exists():
            for format_type in ["svg", "png"]:
                graph_file = CATALOG_ANALYTICS_DIR / f"relationships_graph.{format_type}"
                if graph_file.exists():
                    graph_files.append(str(graph_file))
        return graph_files
    
    def display_join_analysis(self, join_analysis: Dict):
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
    
    def display_query_card(self, row, index: int):
        """Display a single query card using pre-parsed data for optimal performance"""
        query = safe_get_value(row, 'query')
        description = safe_get_value(row, 'description')
        
        # Use pre-parsed columns (available from optimized_queries.parquet/csv)
        if 'tables_parsed' in row and isinstance(row['tables_parsed'], list):
            tables_list = row['tables_parsed']
        else:
            # Fallback for original CSV data
            tables_raw = safe_get_value(row, 'tables')
            tables_list = [t.strip() for t in tables_raw.split(',') if t.strip()] if tables_raw else []
        
        if 'joins_parsed' in row and isinstance(row['joins_parsed'], list):
            joins_list = row['joins_parsed']
        else:
            # Fallback for original CSV data
            joins_raw = safe_get_value(row, 'joins')
            joins_list = [j.strip() for j in joins_raw.split(',') if j.strip()] if joins_raw else []
        
        # Create expandable card
        with st.container():
            # Card header with query title/description
            card_title = description if description else f"Query {index + 1}"
            
            with st.expander(f"📄 {card_title}", expanded=False):
                # Query content
                st.code(query, language="sql")
                
                # Metadata in columns
                if tables_list or joins_list:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if tables_list:
                            st.markdown("**🗂️ Tables:**")
                            for table in tables_list[:5]:  # Limit display
                                st.caption(f"• {table}")
                            if len(tables_list) > 5:
                                st.caption(f"... and {len(tables_list) - 5} more")
                    
                    with col2:
                        if joins_list:
                            st.markdown("**🔗 Joins:**")
                            for join in joins_list[:3]:  # Limit display
                                if isinstance(join, dict):
                                    # Format join info nicely
                                    join_desc = f"{join.get('left_table', 'Unknown')} → {join.get('right_table', 'Unknown')}"
                                    if join.get('join_type'):
                                        join_desc += f" ({join['join_type']})"
                                    st.caption(f"• {join_desc}")
                                else:
                                    st.caption(f"• {join}")
                            if len(joins_list) > 3:
                                st.caption(f"... and {len(joins_list) - 3} more")
    
    def search_queries(self, df: pd.DataFrame, search_term: str) -> pd.DataFrame:
        """Search queries using pre-parsed data for efficiency"""
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
        
        return filtered_df
    
    def render_pagination_controls(self, filtered_df: pd.DataFrame):
        """Render pagination controls and return current page"""
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
        
        return current_page, pagination_info
    
    def render_navigation_hints(self, current_page: int, pagination_info: Dict):
        """Render navigation hints for large datasets"""
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
    
    def render_analytics_error(self):
        """Render error message when analytics cache is not available"""
        st.error("❌ **Analytics cache not available**")
        st.error("🚫 **Query Catalog requires pre-computed analytics for optimal performance**")
        st.code("""
# Run this command to generate analytics cache:
python catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv"
        """)
        st.stop()
    
    def render(self):
        """Render the complete catalog page"""
        st.title(self.page_title)
        
        # Load required data
        if not session_manager.load_csv_data_if_needed():
            return
        
        df = session_manager.get_csv_data()
        st.caption(f"Browse all {len(df)} SQL queries with their metadata")
        
        # Try to load cached analytics
        cached_analytics = self.load_cached_analytics()
        
        # Search/filter functionality
        search_term = st.text_input(
            "🔍 Search queries:", 
            placeholder="Search by query content, description, or tables...",
            key="catalog_search"
        )
        
        # Filter dataframe based on search
        filtered_df = self.search_queries(df, search_term)
        
        # Display analytics - ONLY use cached analytics (no fallback computation)
        if cached_analytics:
            # Use cached analytics for much faster display
            join_analysis = cached_analytics['join_analysis']
            
            # Only show full analytics for non-search results to avoid confusion
            if not search_term:
                self.display_join_analysis(join_analysis)
                
                # Load and display cached graphs
                graph_files = self.load_cached_graph_files()
                if graph_files and len(join_analysis.get('relationships', [])) > 0:
                    st.subheader("🌐 Table Relationship Graph")
                    
                    # Display the first available graph
                    graph_file = Path(graph_files[0])
                    if graph_file.suffix.lower() == '.svg':
                        # Display SVG graph
                        try:
                            with open(graph_file, 'r') as f:
                                svg_content = f.read()
                            st.image(svg_content, use_column_width=True)
                        except Exception as e:
                            st.warning(f"Could not display SVG graph: {e}")
                    else:
                        # Display PNG/other formats
                        try:
                            st.image(str(graph_file), use_column_width=True)
                        except Exception as e:
                            st.warning(f"Could not display graph: {e}")
                    
                    st.caption(f"Graph loaded from cache: {graph_file.name}")
            else:
                # For search results, show simple stats only
                st.info(f"📊 Showing {len(filtered_df)} search results (full analytics available for complete dataset)")
        else:
            # NO FALLBACK COMPUTATION - require cache
            if not CATALOG_ANALYTICS_DIR.exists():
                st.error("🚫 **Query Catalog requires pre-computed analytics**")
                st.error(f"❌ Analytics cache directory not found: `{CATALOG_ANALYTICS_DIR}`")
                st.code("""
# Generate analytics cache first:
python catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv"
                """)
            else:
                st.error("❌ **Analytics files are missing or incomplete**")
                st.error("🔄 **Cache may need to be regenerated**")
                st.code("""
# Regenerate complete analytics cache:
python catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv" --force-rebuild
                """)
            st.stop()
        
        st.divider()
        
        # Display queries with pagination to prevent freezing
        st.subheader(f"📋 Queries ({len(filtered_df)} total)")
        
        if len(filtered_df) == 0:
            st.warning("No queries found matching your search criteria")
            return
        
        # Pagination controls
        current_page, pagination_info = self.render_pagination_controls(filtered_df)
        
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
            self.display_query_card(row, global_index)
        
        # Add navigation hints for large datasets
        self.render_navigation_hints(current_page, pagination_info)


# Global instance
catalog_page = CatalogPage()