#!/usr/bin/env python3
"""
UI Page Functions
UI page functions extracted from app_simple_gemini.py for better organization
"""

import sys
import os
import time
import logging
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import pandas as pd
import streamlit as st

# Import utility functions
from utils.app_utils import (
    calculate_conversation_tokens,
    safe_get_value,
    get_user_session_id,
    auto_save_conversation,
    detect_chat_agent_type,
    get_chat_agent_indicator
)

# Import configuration
try:
    from config.app_config import app_config
    SCHEMA_CSV_PATH = app_config.SCHEMA_CSV_PATH
except ImportError:
    # Fallback configuration
    SCHEMA_CSV_PATH = Path(__file__).parent.parent / "data_new" / "thelook_ecommerce_schema.csv"

# Import data loading functions
from data.app_data_loader import load_lookml_safe_join_map

logger = logging.getLogger(__name__)


def create_query_catalog_page(df: pd.DataFrame):
    """Create comprehensive query catalog page with analytics and pagination"""
    st.title("📋 Query Catalog")
    st.caption("Browse and analyze your query collection with detailed analytics")
    
    if df is None or df.empty:
        st.error("❌ No query data available")
        st.info("💡 Load a CSV file with queries first")
        return
    
    # Load analytics if available
    analytics = load_cached_analytics()
    
    # Display analytics section
    if analytics:
        display_catalog_analytics(analytics, df)
    
    st.divider()
    
    # Query browsing with search and pagination
    query_browser = create_query_browser(df)
    
    # Display selected queries
    if query_browser['selected_indices']:
        display_selected_queries(df.iloc[query_browser['selected_indices']])


def create_data_page(schema_manager):
    """Create Data/Page schema browsing page"""
    st.title("📊 Dataset Schema")
    
    if not schema_manager:
        st.error("❌ Schema not available. Ensure data_new/thelook_ecommerce_schema.csv exists.")
        st.stop()
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tables", schema_manager.table_count)
    with col2:
        st.metric("Columns", schema_manager.column_count)
    with col3:
        st.caption(f"Source: schema CSV")
    
    st.divider()
    st.subheader("🔎 Browse Tables")
    
    # Search + list of tables
    search = st.text_input("Search tables", "", help="Filter tables by name (substring)")
    try:
        all_tables = sorted(list(schema_manager.schema_lookup.keys()))
    except Exception:
        all_tables = []
    filtered = [t for t in all_tables if (search.lower() in t.lower())] if search else all_tables
    
    if not filtered:
        st.info("No tables matched your search.")
        return
    
    # Table expanders with columns and datatypes (matching original logic)
    df_schema = getattr(schema_manager, 'schema_df', None)
    max_show = len(filtered)
    for t in filtered[:max_show]:
        fqn = getattr(schema_manager, 'get_fqn', lambda x: x)(t)
        with st.expander(t, expanded=False):
            st.caption(f"FQN: `{fqn}`")
            if df_schema is not None:
                try:
                    norm = schema_manager._normalize_table_name(t)
                    table_df = df_schema[df_schema['table_id'] == norm][['column', 'datatype']].reset_index(drop=True)
                    st.dataframe(table_df, use_container_width=True, hide_index=True)
                except Exception:
                    cols = schema_manager.get_table_columns(t)
                    st.write(", ".join(cols) if cols else "No columns")
            else:
                cols = schema_manager.get_table_columns(t)
                st.write(", ".join(cols) if cols else "No columns")


def create_chat_page(vector_store, csv_data):
    """Create ChatGPT-like chat conversation page with Gemini mode"""
    # Initialize chat messages in session state
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    # Calculate real-time token usage
    token_stats = calculate_conversation_tokens(st.session_state.chat_messages)
    
    # Chat interface
    display_chat_header(token_stats, csv_data)
    
    # Message history
    display_chat_messages()
    
    # Chat input
    handle_chat_input(vector_store, csv_data)


def create_introduction_page():
    """Create introduction/onboarding page"""
    st.markdown("""
    # 🚀 Welcome to Your AI-Powered SQL Assistant
    
    **Transform the way you interact with data using natural language!**
    
    ---
    
    ## 🎯 What You Can Do
    
    ### 📝 **Ask Questions in Plain English**
    - "Show me all users who joined last month"
    - "What's our revenue by product category?"
    - "How many orders were placed vs cancelled?"
    
    ### 🔧 **Generate SQL Queries**
    - Get production-ready SQL automatically
    - Follow best practices and performance optimization
    - Include proper joins and aggregations
    
    ### 📊 **Explore Your Data**
    - Browse table relationships and schemas
    - Understand data patterns and statistics
    - Discover insights through AI analysis
    
    ---
    
    ## 🚀 Getting Started
    
    1. **📋 Browse Query Catalog** - Explore example queries and patterns
    2. **📊 View Data Schema** - Understand your database structure  
    3. **💬 Start Chatting** - Ask questions naturally
    
    ---
    
    ## ⚡ Key Features
    
    - 🤖 **Powered by Google Gemini** - Advanced AI for SQL generation
    - 🛡️ **Safe SQL Execution** - Validated and sandboxed queries
    - 📈 **Real-time Analytics** - Token usage and performance metrics
    - 💾 **Conversation Memory** - Context-aware conversations
    - 🔍 **Smart Schema Injection** - Relevant table suggestions
    
    ---
    
    ## 🎯 Ready to Go?
    
    Navigate using the sidebar and start exploring your data! 🚀
    """)


# Helper functions for the pages

def load_cached_analytics():
    """Load cached analytics data"""
    try:
        analytics_path = Path(__file__).parent.parent / "catalog_analytics" / "join_analysis.json"
        if analytics_path.exists():
            with open(analytics_path) as f:
                return json.load(f)
    except Exception:
        pass
    return None


def display_catalog_analytics(analytics, df):
    """Display analytics section for catalog page"""
    st.subheader("📊 Analytics Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Queries", len(df))
    
    with col2:
        unique_tables = analytics.get('metadata', {}).get('unique_tables', len(set()))
        st.metric("Unique Tables", unique_tables)
    
    with col3:
        joins_found = analytics.get('metadata', {}).get('queries_with_joins', 0)
        st.metric("Queries with Joins", joins_found)
    
    with col4:
        avg_complexity = analytics.get('metadata', {}).get('avg_joins_per_query', 0)
        st.metric("Avg Joins/Query", f"{avg_complexity:.1f}")


def create_query_browser(df):
    """Create query browser with search and pagination"""
    # Search functionality
    search_query = st.text_input("🔍 Search queries", "", help="Search in query text or descriptions")
    
    # Pagination controls
    page_size = 15
    total_pages = max(1, (len(df) + page_size - 1) // page_size)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⬅️ Previous"):
            if st.session_state.get('catalog_page', 1) > 1:
                st.session_state.catalog_page = st.session_state.get('catalog_page', 1) - 1
    
    with col2:
        current_page = st.session_state.get('catalog_page', 1)
        st.write(f"Page {current_page} of {total_pages}")
    
    with col3:
        if st.button("Next ➡️"):
            if st.session_state.get('catalog_page', 1) < total_pages:
                st.session_state.catalog_page = st.session_state.get('catalog_page', 1) + 1
    
    # Filter and paginate data
    if search_query:
        filtered_df = df[
            df['query'].str.contains(search_query, case=False, na=False) |
            df['description'].str.contains(search_query, case=False, na=False)
        ]
    else:
        filtered_df = df
    
    # Paginate
    current_page = st.session_state.get('catalog_page', 1)
    start_idx = (current_page - 1) * page_size
    end_idx = start_idx + page_size
    page_df = filtered_df.iloc[start_idx:end_idx]
    
    # Multi-select for queries
    selected_indices = []
    for i, (_, row) in enumerate(page_df.iterrows()):
        actual_idx = filtered_df.index.get_loc(row.name)
        if st.checkbox(
            f"{row.get('description', row.get('query', ''))[:50]}...",
            key=f"query_{actual_idx}"
        ):
            selected_indices.append(actual_idx)
    
    return {
        'selected_indices': selected_indices,
        'filtered_df': filtered_df,
        'page_df': page_df
    }


def display_selected_queries(selected_df):
    """Display details for selected queries"""
    st.subheader("📋 Selected Query Details")
    
    for _, row in selected_df.iterrows():
        with st.expander(f"Query: {row.get('description', 'No description')[:50]}..."):
            col1, col2 = st.columns(2)
            
            with col1:
                st.code(row.get('query', ''), language="sql")
            
            with col2:
                st.write("**Metadata:**")
                for col in selected_df.columns:
                    if col != 'query' and pd.notna(row[col]):
                        st.write(f"- {col}: {row[col]}")





def display_chat_header(token_stats, csv_data):
    """Display chat header with token stats and controls"""
    # Token usage display
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.write(f"📊 {token_stats.get('total_tokens', 0):,} tokens")
    
    with col2:
        st.write(f"📝 {len(st.session_state.chat_messages)} messages")
    
    with col3:
        utilization = token_stats.get('utilization_percent', 0)
        st.write(f"🔥 {utilization:.1f}% context")


def display_chat_messages():
    """Display chat message history"""
    for message in st.session_state.chat_messages:
        if message.get('role') == 'user':
            with st.chat_message('user'):
                st.write(message.get('content', ''))
        else:
            with st.chat_message('assistant'):
                st.write(message.get('content', ''))
                
                # Show sources if available
                if message.get('sources'):
                    with st.expander("📚 Sources"):
                        for i, source in enumerate(message['sources']):
                            st.write(f"{i+1}. {source.metadata.get('source', 'Unknown')}")


def handle_chat_input(vector_store, csv_data):
    """Handle chat input and processing"""
    if prompt := st.chat_input("Ask about your data in plain English..."):
        # Add user message
        st.session_state.chat_messages.append({
            'role': 'user',
            'content': prompt,
            'timestamp': time.time()
        })
        
        # Process the question (this would call the RAG pipeline)
        # For now, just show a placeholder response
        response = f"I understand you're asking about: {prompt}. This is a placeholder response."
        
        st.session_state.chat_messages.append({
            'role': 'assistant',
            'content': response,
            'timestamp': time.time()
        })
        
        # Auto-save conversation
        auto_save_conversation()
        
        # Rerun to show new messages
        st.rerun()