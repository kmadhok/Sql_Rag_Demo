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

# Import RAG functions
try:
    # To avoid circular imports, we'll get this from session_state or use placeholder
    answer_question_chat_mode = None
except ImportError:
    # Fallback if file not available
    answer_question_chat_mode = None

def get_answer_question_function():
    """Get the answer_question_chat_mode function from main app to avoid circular imports"""
    try:
        # Try to get from session_state if main app set it there
        if hasattr(st.session_state, '_answer_question_chat_mode'):
            return st.session_state._answer_question_chat_mode
        
        # Otherwise, import dynamically (with circular import handling)
        import importlib
        main_module = importlib.import_module('app_simple_gemini')
        return main_module.answer_question_chat_mode
    except (ImportError, AttributeError):
        return None

def extract_sql_with_llm(text_response):
    """Extract SQL from AI response using lightweight LLM approach"""
    try:
        # Get LLM client (reuse existing gemini client)
        try:
            # Import gemini client (same as main app uses)
            from gemini_client import GeminiClient
            
            # Reuse existing client if available in session
            if hasattr(st.session_state, 'gemini_client'):
                llm_client = st.session_state.gemini_client
            else:
                # Create new client
                from config.safe_config import safe_config
                llm_client = GeminiClient(
                    api_key='AIzaSyCbVNMFP8wBwtMb6trHWFESiTmhENst2io',
                    model="gemini-2.5-flash-lite"  # Use same model as chat for consistency
                )
                st.session_state.gemini_client = llm_client
                
        except ImportError:
            logger.warning("Gemini client not available for SQL extraction")
            return None
        
        # Create extraction prompt
        extraction_prompt = f"""Extract ONLY the complete SQL query from this AI response. Return the exact SQL and nothing else.

STRICT RULES:
1. Return ONLY the SQL query, no comments, no explanations, no descriptions
2. Remove any leading comments like "-- explanation"
3. Start directly with the SQL keyword (SELECT, WITH, etc.)
4. Include all parts: WITH clauses, CTEs, SELECT statements, UNION ALL, etc.
5. End with semicolon
6. Remove any markdown code blocks
7. Do not add any prefixes or suffixes
8. Make sure the SQL is ready to execute immediately

Good Example of what to return:
SELECT * FROM users WHERE created_at >= '2024-01-01';

Bad Example of what NOT to return:
-- This query selects users
SELECT * FROM users WHERE created_at >= '2024-01-01';

AI Response to extract from:
```
{text_response}
```

Return ONLY the SQL:"""
        
        # Call LLM for extraction
        logger.debug("🤖 Calling LLM for SQL extraction")
        extraction_result = llm_client.invoke(extraction_prompt)
        
        if extraction_result:
            extracted_query = extraction_result.strip()
            
            # Clean up the result
            # Remove any markdown code blocks if present
            if extracted_query.startswith('```sql'):
                extracted_query = extracted_query[6:]
            if extracted_query.startswith('```'):
                extracted_query = extracted_query[3:]
            if extracted_query.endswith('```'):
                extracted_query = extracted_query[:-3]
            
            extracted_query = extracted_query.strip()
            
            # Remove leading comments and whitespace to find the actual SQL
            lines = extracted_query.split('\n')
            sql_start_idx = 0
            
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                if (stripped_line.startswith('SELECT') or 
                    stripped_line.startswith('WITH') or 
                    stripped_line.startswith('INSERT') or 
                    stripped_line.startswith('UPDATE') or 
                    stripped_line.startswith('DELETE') or 
                    stripped_line.startswith('CREATE')):
                    sql_start_idx = i
                    break
            
            # Rebuild from the first SQL line found
            if sql_start_idx > 0:
                extracted_query = '\n'.join(lines[sql_start_idx:])
            
            # Final strip
            extracted_query = extracted_query.strip()
            
            # Validate the extracted SQL
            if _looks_like_complete_sql(extracted_query):
                logger.info(f"✅ LLM extraction validated: {len(extracted_query)} chars")
                return extracted_query
            else:
                logger.warning(f"⚠️ LLM extraction failed validation: {extracted_query[:100]}...")
                # Don't return invalid SQL
                return None
        else:
            logger.warning("🤖 LLM returned empty result for SQL extraction")
            return None
            
    except Exception as e:
        logger.error(f"❌ LLM SQL extraction error: {e}")
        return None

def extract_sql_with_patterns(text_response):
    """Fallback regex patterns for SQL extraction (only used as last resort)"""
    try:
        # Enhanced SQL extraction patterns for complex queries
        import re
        sql_patterns = [
            # 1. SQL code blocks with language tag (highest priority)
            (r'```sql\s*([^`]+)```', 1, 'SQL code block'),
            
            # 2. Generic code blocks (medium priority)
            (r'```([^`]*)```', 1, 'Generic code block'),
            
            # 3. Complete WITH clause + following SELECT statements (most complex pattern)
            (r'(WITH\s+[^;]+(?:SELECT[^;]+(?:\s+(?:UNION\s+ALL\s+)?SELECT[^;]*)*)+)', 1, 'WITH + SELECT'),
            
            # 4. Complete multi-statement SQL (handles UNION, etc.)
            (r'(SELECT\s+[^;]*(?:\s+(?:UNION\s+(?:ALL\s+)?SELECT[^;]*)*)*)', 1, 'Multi-statement SELECT'),
            
            # 5. Single SELECT statement (fallback)
            (r'SELECT[^;]+', 0, 'Single SELECT')
        ]
        
        for pattern, group_idx, pattern_name in sql_patterns:
            match = re.search(pattern, text_response, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    if group_idx > 0:
                        extracted_sql = match.group(group_idx).strip()
                    else:
                        extracted_sql = match.group(0).strip()
                    
                    # Clean up common SQL issues
                    if extracted_sql:
                        # Remove leading/trailing quotes if present
                        extracted_sql = extracted_sql.strip('\'\'')
                        
                        # Fix common pattern: stray closing parenthesis
                        if extracted_sql.startswith(')') and not extracted_sql.startswith(')\s*SELECT'):
                            # This often happens when WITH clause parsing goes wrong
                            extracted_sql = 'WITH UserOrderCount AS (' + extracted_sql
                        
                        logger.info(f"🎯 {pattern_name} pattern extraction found {len(extracted_sql)} chars: {extracted_sql[:60]}...")
                        
                        # Validate that this looks like complete SQL
                        if _looks_like_complete_sql(extracted_sql):
                            # Found complete SQL!
                            logger.info(f"✅ Complete SQL extracted using {pattern_name} pattern")
                            return extracted_sql
                        else:
                            logger.info(f"⚠️ Incomplete SQL from {pattern_name}, trying next pattern")
                            continue
                        
                except Exception as pattern_error:
                    logger.warning(f"Pattern error for {pattern_name} {pattern}: {pattern_error}")
                    continue
        
        logger.warning(f"❌ No valid SQL extracted from {len(text_response)} character response using any pattern")
        logger.debug(f"Full response for debugging: {text_response}")
        return None
        
    except Exception as e:
        logger.error(f"Regex pattern extraction error: {e}")
        return None

def _looks_like_complete_sql(sql_text):
    """Helper function to validate if extracted text looks like complete SQL"""
    if not sql_text or len(sql_text.strip()) < 10:
        return False
    
    sql_upper = sql_text.strip().upper()
    
    # Must contain valid SQL keyword (allow comments before)
    has_sql_keyword = any(sql_upper.startswith(keyword) for keyword in [
        'SELECT', 'WITH', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER',
        'TRUNCATE', 'INSERT', 'MERGE', 'CALL', 'EXEC'
    ])
    
    # Also check if it contains SQL keyword anywhere (in case of leading comments)
    if not has_sql_keyword:
        contains_sql_keyword = any(keyword in sql_upper for keyword in [
            'SELECT', 'WITH', 'INSERT', 'UPDATE', 'DELETE', 'CREATE'
        ])
        if not contains_sql_keyword:
            logger.debug(f"No SQL keyword found in: {sql_text[:50]}...")
            return False
    
    # Check for obviously broken patterns
    # 1. Starts with ')' but doesn't start with ') SELECT' (indicates truncated WITH clause)
    if sql_upper.startswith(')') and not sql_upper.startswith(')\s*SELECT'):
        logger.debug("SQL starts with stray closing parenthesis - likely truncated WITH clause")
        return False
    
    # 2. Has ')' at beginning of line without proper opening parenthesis before it
    if re.search(r'^\s*\)', sql_text, re.MULTILINE) and not re.search(r'WITH.*\n\s*\)', sql_text, re.DOTALL | re.IGNORECASE):
        logger.debug("SQL has stray closing parenthesis - likely incomplete")
        return False
    
    # Check for balanced parentheses (basic check)
    open_parens = sql_text.count('(')
    close_parens = sql_text.count(')')
    
    # If SELECT starts but WITH clause ends abruptly, reject
    if sql_upper.startswith('SELECT') and 'GROUP BY user_id' in sql_upper and sql_text.strip().startswith(')'):
        logger.debug("SELECT statement truncated in middle of GROUP BY")
        return False
    
    # Allow for some imbalance (due to complex statements), but not wild imbalance
    if abs(open_parens - close_parens) > 3:
        logger.debug(f"Severe unbalanced parentheses: {open_parens} open, {close_parens} close")
        return False
    
    # Check if it has a proper ending (semicolon or complete structure)
    has_ending = (
        sql_text.strip().endswith(';') or  # Ends with semicolon
        (sql_upper.startswith('SELECT') and 'FROM' in sql_upper) or  # SELECT with FROM
        (sql_upper.startswith('WITH') and 'SELECT' in sql_upper)  # WITH with SELECT
    )
    
    # For WITH clauses, they should include SELECT statements
    if sql_upper.startswith('WITH'):
        if 'SELECT' not in sql_upper:
            logger.debug("WITH clause without SELECT - incomplete")
            return False
    
    # For SELECT statements, they should have FROM (unless it's VALUES)
    if sql_upper.startswith('SELECT') and 'FROM' not in sql_upper and 'VALUES' not in sql_upper:
        logger.debug("SELECT without FROM or VALUES - likely incomplete")
        return False
    
    # Check for common SQL keywords that indicate completeness
    has_common_keywords = any(keyword in sql_upper for keyword in [
        'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'UNION', 'JOIN'
    ])
    
    logger.debug(f"SQL validation: has_ending={has_ending}, has_keywords={has_common_keywords}")
    
    return has_ending or has_common_keywords

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
                    st.dataframe(table_df, width="stretch", hide_index=True)
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


def render_assistant_message_with_sql(message, message_index):
    """Render assistant message with SQL execution capabilities for @create agent"""
    st.write(message.get('content', ''))
    
    # Show sources if available
    if message.get('sources'):
        with st.expander("📚 Sources"):
            for i, source in enumerate(message['sources']):
                st.write(f"{i+1}. {source.metadata.get('source', 'Unknown')}")
    
    # SQL Section (only for @create agent)
    if message.get('agent_type') == 'create' and message.get('sql_query'):
        with st.expander("💾 Generated SQL", expanded=False):
            st.code(message['sql_query'], language="sql")
            
            # SQL Execution Controls
            if not message.get('sql_executed'):
                col1, col2 = st.columns([1, 2])
                with col1:
                    if st.button(
                        "▶️ Execute SQL", 
                        key=f"exec_sql_{message_index}",
                        help="Execute this SQL query in BigQuery",
                        type="primary"
                    ):
                        execute_chat_sql(message_index)
                with col2:
                    st.caption("💡 Executes in BigQuery read-only mode")
            else:
                # Show execution results
                display_chat_sql_results(message)


def display_chat_messages():
    """Display chat message history with SQL execution capabilities"""
    for idx, message in enumerate(st.session_state.chat_messages):
        if message.get('role') == 'user':
            with st.chat_message('user'):
                st.write(message.get('content', ''))
        else:
            with st.chat_message('assistant'):
                render_assistant_message_with_sql(message, idx)


def process_chat_response(vector_store, csv_data, user_input):
    """Process chat response with SQL extraction for @create agent using real RAG pipeline"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Detect @create agent
        agent_type, question = detect_chat_agent_type(user_input)
        
        # Get conversation context
        conversation_context = ""
        for msg in st.session_state.chat_messages:
            if msg.get('role') == 'user':
                conversation_context += f"User: {msg['content']}\n"
            else:
                # Skip previous assistant messages to avoid context bloat
                if len(msg.get('content', '')) < 500:  # Only include short messages
                    conversation_context += f"Assistant: {msg['content'][:200]}\n"
        
        # Get managers from session state
        schema_manager = st.session_state.get('schema_manager')
        
        # Call the real RAG pipeline
        logger.info(f"🤖 Processing chat with agent_type: {agent_type}")
        
        try:
            # Get the function dynamically to avoid circular imports
            answer_function = get_answer_question_function()
            if answer_function is None:
                raise ImportError("answer_question_chat_mode not available")
                
            result = answer_function(
                question=question,
                vector_store=vector_store,
                k=20,  # Retrieve more documents for @create
                schema_manager=schema_manager,
                conversation_context=conversation_context,
                agent_type=agent_type,
                user_context="",
                excluded_tables=[]
            )
            
            if result:
                answer, sources, token_usage = result
                logger.info(f"✅ RAG pipeline success: {len(answer)} chars, {len(sources)} sources")
            else:
                # Fallback response if RAG fails
                answer = (f"I apologize, but I couldn't process your request for: {question}. "
                        f"Please try rephrasing your question.")
                sources = []
                token_usage = {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}
        
        except Exception as rag_error:
            logger.error(f"RAG pipeline error: {rag_error}")
            answer = f"I encountered an error while processing your request: {str(rag_error)}"
            sources = []
            token_usage = {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}
        
        # Extract SQL from @create response
        extracted_sql = None
        if agent_type == 'create' and answer:
            logger.info(f"🔍 Starting SQL extraction for @create response ({len(answer)} chars)")
            logger.info(f"📝 @create FULL response:\n[START]\n{answer}\n[END]")
            logger.debug(f"📝 @create response preview: {answer[:200]}...")
            
            # Try our dedicated extraction service first
            try:
                from services.sql_extraction_service import extract_sql_from_text
                logger.info("🔧 Using dedicated SQL extraction service")
                extracted_sql = extract_sql_from_text(answer, debug=True)
                
                if extracted_sql:
                    logger.info(f"✅ Extraction service successful: {len(extracted_sql)} chars")
                    logger.info(f"🎯 Extracted SQL: {extracted_sql}")
                else:
                    logger.warning("❌ Extraction service found no SQL")
                    
            except Exception as extraction_error:
                logger.error(f"💥 Extraction service error: {extraction_error}")
                extracted_sql = None
            
            # Fallback to executor if service fails
            if not extracted_sql:
                try:
                    executor = st.session_state.get('bigquery_executor')
                    if executor:
                        extracted_sql = executor.extract_sql_from_text(answer)
                        logger.info(f"🔍 Executor extraction result: {'success' if extracted_sql else 'no SQL found'}")
                        if extracted_sql:
                            logger.info(f"🎯 Executor extracted: {extracted_sql}")
                except Exception as executor_error:
                    logger.error(f"💥 Executor error: {executor_error}")
                    extracted_sql = None
                    import re
                    sql_patterns = [
                        # 1. SQL code blocks with language tag (highest priority)
                        (r'```sql\s*([^`]+)```', 1, 'SQL code block'),
                        
                        # 2. Generic code blocks (medium priority)
                        (r'```([^`]*)```', 1, 'Generic code block'),
                        
                        # 3. Complete WITH clause + following SELECT statements (most complex pattern)
                        (r'(WITH\s+[^;]+(?:SELECT[^;]+(?:\s+(?:UNION\s+ALL\s+)?SELECT[^;]*)*)+)', 1, 'WITH + SELECT'),
                        
                        # 4. Complete multi-statement SQL (handles UNION, etc.)
                        (r'(SELECT\s+[^;]*(?:\s+(?:UNION\s+(?:ALL\s+)?SELECT[^;]*)*)*)', 1, 'Multi-statement SELECT'),
                        
                        # 5. Single SELECT statement (fallback)
                        (r'SELECT[^;]+', 0, 'Single SELECT')
                    ]
                    
                    for pattern, group_idx, pattern_name in sql_patterns:
                        match = re.search(pattern, answer, re.IGNORECASE | re.DOTALL)
                        if match:
                            try:
                                if group_idx > 0:
                                    extracted_sql = match.group(group_idx).strip()
                                else:
                                    extracted_sql = match.group(0).strip()
                                
                                # Clean up common SQL issues
                                if extracted_sql:
                                    # Remove leading/trailing quotes if present
                                    extracted_sql = extracted_sql.strip('\'\'')
                                    
                                    # Fix common pattern: stray closing parenthesis
                                    if extracted_sql.startswith(')') and not extracted_sql.startswith(')\s*SELECT'):
                                        # This often happens when WITH clause parsing goes wrong
                                        extracted_sql = 'WITH UserOrderCount AS (' + extracted_sql
                                    
                                    logger.info(f"🎯 {pattern_name} extraction found {len(extracted_sql)} chars: {extracted_sql[:60]}...")
                                    
                                    # Validate that this looks like complete SQL
                                    if _looks_like_complete_sql(extracted_sql):
                                        # Found complete SQL!
                                        logger.info(f"✅ Complete SQL extracted using {pattern_name} pattern")
                                        break
                                    else:
                                        logger.info(f"⚠️ Incomplete SQL from {pattern_name}, trying next pattern")
                                        extracted_sql = None
                                        continue
                                
                            except Exception as pattern_error:
                                logger.warning(f"Pattern error for {pattern_name} {pattern}: {pattern_error}")
                                continue
                    
                    if extracted_sql:
                        if extracted_sql:
                            logger.info(f"✅ Final SQL extraction successful: {len(extracted_sql)} chars")
                            logger.info(f"🎯 Final SQL: {extracted_sql}")
                        else:
                            logger.warning(f"❌ No valid SQL extracted from {len(answer)} character response")
                            logger.debug(f"Full response for debugging: {answer}")
        
        # Create enhanced message with SQL support
        message_data = {
            'role': 'assistant',
            'content': answer,
            'agent_type': agent_type,
            'sources': sources,
            'token_usage': token_usage,
            'sql_query': extracted_sql,
            'sql_executed': False,
            'sql_result': None,
            'sql_execution_id': None,
            'timestamp': time.time()
        }
        
        # Log SQL extraction success
        if agent_type == 'create':
            if extracted_sql:
                logger.info(f"✅ SQL extracted for @create: {len(extracted_sql)} chars")
            else:
                logger.warning(f"⚠️ No SQL extracted from @create response")
        
        return message_data
        
    except Exception as e:
        logger.error(f"Error processing chat response: {e}")
        # Fallback response
        return {
            'role': 'assistant',
            'content': f"I encountered an error processing your request: {str(e)}. Please try again.",
            'timestamp': time.time()
        }


def handle_chat_input(vector_store, csv_data):
    """Handle chat input and processing with SQL extraction"""
    if prompt := st.chat_input("Ask about your data in plain English..."):
        # Add user message
        st.session_state.chat_messages.append({
            'role': 'user',
            'content': prompt,
            'timestamp': time.time()
        })
        
        # Process the question with SQL extraction
        response = process_chat_response(vector_store, csv_data, prompt)
        
        # Add assistant response
        st.session_state.chat_messages.append(response)
        
        # Auto-save conversation
        auto_save_conversation()
        
        # Rerun to show new messages
        st.rerun()


def execute_chat_sql(message_index):
    """Execute SQL from chat message"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Get the message
        message = st.session_state.chat_messages[message_index]
        sql_query = message.get('sql_query')
        
        if not sql_query:
            st.error("❌ No SQL query found to execute")
            return
        
        # Initialize BigQuery executor if needed
        executor = st.session_state.get('bigquery_executor')
        if not executor:
            try:
                from core.bigquery_executor import BigQueryExecutor
                executor = BigQueryExecutor()
                st.session_state.bigquery_executor = executor
                logger.info("🔧 Initialized BigQuery executor for chat")
            except Exception as e:
                st.error(f"❌ Failed to initialize BigQuery executor: {e}")
                return
        
        # Safety validation
        from security.sql_validator import validate_sql_legacy_wrapper
        is_valid, validation_msg = validate_sql_legacy_wrapper(sql_query)
        
        if not is_valid:
            st.error(f"🚫 Safety validation failed: {validation_msg}")
            logger.warning(f"🚫 Chat SQL validation failed: {validation_msg}")
            return
        
        # Execute query with progress indicator
        with st.spinner(f"🔄 Executing SQL query..."):
            try:
                result = executor.execute_query(
                    sql_query,
                    dry_run=False,  # Could be configurable later
                    max_bytes_billed=100_000_000
                )
                
                # Update message with results
                message['sql_result'] = result
                message['sql_executed'] = True
                message['sql_execution_time'] = time.time()
                message['sql_execution_id'] = f"chat_{message_index}_{int(time.time())}"
                
                # Update session state
                st.session_state.chat_messages[message_index] = message
                
                if result.success:
                    st.success("✅ SQL executed successfully!")
                    logger.info(f"✅ Chat SQL execution successful: {result.total_rows} rows")
                else:
                    st.error(f"❌ SQL execution failed: {result.error_message}")
                    logger.error(f"❌ Chat SQL execution failed: {result.error_message}")
                
            except Exception as e:
                st.error(f"❌ SQL execution error: {e}")
                logger.error(f"❌ Chat SQL execution error: {e}")
                
                # Still mark as executed (but failed)
                message['sql_executed'] = True
                message['sql_result'] = None
                message['sql_execution_time'] = time.time()
                message['sql_execution_id'] = f"chat_{message_index}_{int(time.time())}"
                st.session_state.chat_messages[message_index] = message
        
        # Auto-save conversation after SQL execution
        auto_save_conversation()
        
        # Rerun to show results
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Unexpected error during SQL execution: {e}")
        logger.error(f"❌ Unexpected chat SQL execution error: {e}")


def display_chat_sql_results(message):
    """Display SQL execution results in chat"""
    result = message.get('sql_result')
    
    if not result:
        st.error("❌ No execution result available")
        return
    
    if result.success:
        st.success(f"✅ Query executed successfully")
        
        with st.expander("📊 Query Results", expanded=True):
            # Show execution metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                row_count = getattr(result, 'total_rows', 0)
                if hasattr(result, 'data') and result.data is not None:
                    row_count = len(result.data)
                st.metric("Rows", f"{row_count:,}")
            
            with col2:
                cost = getattr(result, 'cost', 0.0)
                st.metric("Cost", f"${cost:.4f}")
            
            with col3:
                bytes_processed = getattr(result, 'bytes_processed', 0)
                st.metric("Bytes", f"{bytes_processed:,}")
            
            with col4:
                exec_time = getattr(result, 'execution_time', 0.0)
                st.metric("Time", f"{exec_time:.2f}s")
            
            # Show data if available
            if hasattr(result, 'data') and result.data is not None and not result.data.empty:
                st.dataframe(result.data, width="stretch")
            else:
                st.info("No data returned from query")
            
            # Show the executed SQL
            st.subheader("🔍 Executed SQL")
            st.code(message.get('sql_query', 'No SQL available'), language="sql")
            
            # Re-execute option
            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button(
                    "🔄 Re-execute SQL", 
                    key=f"reexec_sql_{message.get('sql_execution_id', 'unknown')}",
                    help="Execute this SQL query again"
                ):
                    # Reset execution status
                    message['sql_executed'] = False
                    message['sql_result'] = None
                    # Update session state
                    for i, msg in enumerate(st.session_state.chat_messages):
                        if msg.get('sql_execution_id') == message.get('sql_execution_id'):
                            st.session_state.chat_messages[i] = message
                            break
                    st.rerun()
            with col2:
                st.caption("💡 Re-execute to get fresh data")
    else:
        st.error(f"❌ Query failed: {result.error_message}")
        
        # Show failed SQL for debugging
        st.subheader("🔍 Failed SQL")
        st.code(message.get('sql_query', 'No SQL available'), language="sql")
        
        # Re-execute option for failed queries
        if st.button(
            "🔄 Try Again", 
            key=f"retry_sql_{message.get('sql_execution_id', 'unknown')}",
            help="Try executing this SQL query again"
        ):
            # Reset execution status for retry
            message['sql_executed'] = False
            message['sql_result'] = None
            # Update session state
            for i, msg in enumerate(st.session_state.chat_messages):
                if msg.get('sql_execution_id') == message.get('sql_execution_id'):
                    st.session_state.chat_messages[i] = message
                    break
            st.rerun()