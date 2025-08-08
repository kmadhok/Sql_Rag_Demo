#!/usr/bin/env python3
"""
Simplified Retail-SQL RAG Streamlit App

A basic, Windows-compatible Streamlit interface that directly loads 
pre-built vector stores created by standalone_embedding_generator.py

Usage:
    1. First run: python standalone_embedding_generator.py --csv "your_data.csv"
    2. Then run: streamlit run app_simple.py

Features:
- Direct vector store loading from faiss_indices/ directory
- Simple question/answer interface with source attribution
- Basic token tracking for local Ollama usage
- Windows compatible with no complex processors
"""

import streamlit as st
import pandas as pd
import time
import logging
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
from collections import defaultdict

# LangChain imports
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Optional graph support for join visualization
try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False

# Import our simplified RAG function
from simple_rag_simple import answer_question_simple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
FAISS_INDICES_DIR = Path(__file__).parent / "faiss_indices"
DEFAULT_VECTOR_STORE = "index_queries_with_descriptions (1)"  # Expected index name
CSV_PATH = Path(__file__).parent / "queries_with_descriptions (1).csv"  # CSV data source

# Streamlit page config
st.set_page_config(
    page_title="Simple SQL RAG", 
    page_icon="🔍",
    layout="wide"
)

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
        # Initialize embeddings (same as used in standalone generator)
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
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

def load_csv_data() -> Optional[pd.DataFrame]:
    """
    Load CSV data with graceful handling of missing values
    
    Returns:
        DataFrame with queries or None if loading fails
    """
    try:
        if not CSV_PATH.exists():
            st.error(f"❌ CSV file not found: {CSV_PATH}")
            return None
        
        # Load CSV with safe handling of missing values
        df = pd.read_csv(CSV_PATH)
        
        # Fill NaN values with empty strings for safe processing
        df = df.fillna('')
        
        # Ensure required columns exist
        required_columns = ['query']
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        if missing_cols:
            st.error(f"❌ Missing required columns: {missing_cols}")
            return None
        
        # Remove rows with empty queries
        df = df[df['query'].str.strip() != '']
        
        logger.info(f"✅ Loaded {len(df)} queries from CSV")
        return df
        
    except Exception as e:
        st.error(f"❌ Error loading CSV: {e}")
        logger.error(f"CSV loading error: {e}")
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

def parse_tables_column(tables_value: str) -> List[str]:
    """
    Parse tables column supporting both JSON array format and simple string format
    
    JSON format: ["`project.dataset.table`","`project.dataset.table`"]
    Simple format: "customers, orders" or "customers"
    
    Returns:
        List of clean table names
    """
    if not tables_value or tables_value.strip() == '':
        return []
    
    try:
        # Try to parse as JSON array first
        tables_json = json.loads(tables_value)
        if isinstance(tables_json, list):
            # Extract table names and clean them
            clean_tables = []
            for table in tables_json:
                # Remove backticks and extract just the table name
                clean_table = str(table).strip('`"\'')
                
                # Handle BigQuery format: project.dataset.table -> table
                if '.' in clean_table:
                    table_parts = clean_table.split('.')
                    clean_table = table_parts[-1]  # Take last part (table name)
                
                if clean_table:
                    clean_tables.append(clean_table)
            
            logger.debug(f"Parsed JSON tables: {clean_tables}")
            return clean_tables
            
    except (json.JSONDecodeError, TypeError):
        # Fall back to simple string parsing
        pass
    
    # Simple string format parsing
    try:
        tables_str = str(tables_value).strip()
        if ',' in tables_str:
            # Multiple tables separated by comma
            tables = [t.strip().strip('`"\'') for t in tables_str.split(',')]
        else:
            # Single table
            tables = [tables_str.strip('`"\'')]
        
        # Clean table names (remove BigQuery prefixes)
        clean_tables = []
        for table in tables:
            if table and table != '':
                # Handle BigQuery format: project.dataset.table -> table
                if '.' in table:
                    table_parts = table.split('.')
                    table = table_parts[-1]
                clean_tables.append(table)
        
        logger.debug(f"Parsed string tables: {clean_tables}")
        return clean_tables
        
    except Exception as e:
        logger.warning(f"Failed to parse tables column '{tables_value}': {e}")
        return []

def parse_joins_column(joins_value: str) -> Optional[Dict[str, Any]]:
    """
    Parse joins column supporting both JSON object format and simple string format
    
    JSON format: {"left_table":"project.dataset.table", "left_column":"campaign_id", 
                  "right_table":"project.dataset.table", "right_column":"id", 
                  "join_type":"LEFT JOIN", "transformation":"complex_condition"}
    Simple format: "o.customer_id = c.customer_id"
    
    Returns:
        Dictionary with join information or None if no joins
    """
    if not joins_value or joins_value.strip() == '':
        return None
    
    try:
        # Try to parse as JSON object first
        join_json = json.loads(joins_value)
        if isinstance(join_json, dict):
            # Extract and clean table names
            left_table = str(join_json.get('left_table', '')).strip('`"\'')
            right_table = str(join_json.get('right_table', '')).strip('`"\'')
            
            # Handle BigQuery format: project.dataset.table -> table
            if '.' in left_table:
                left_table = left_table.split('.')[-1]
            if '.' in right_table:
                right_table = right_table.split('.')[-1]
            
            join_info = {
                'left_table': left_table,
                'right_table': right_table,
                'left_column': join_json.get('left_column', ''),
                'right_column': join_json.get('right_column', ''),
                'join_type': join_json.get('join_type', 'JOIN'),
                'transformation': join_json.get('transformation', ''),
                'condition': f"{left_table}.{join_json.get('left_column', '')} = {right_table}.{join_json.get('right_column', '')}",
                'format': 'json'
            }
            
            # If transformation exists, use it as the condition
            if join_info['transformation']:
                join_info['condition'] = join_info['transformation']
            
            logger.debug(f"Parsed JSON join: {join_info}")
            return join_info
            
    except (json.JSONDecodeError, TypeError):
        # Fall back to simple string parsing
        pass
    
    # Simple string format parsing
    try:
        joins_str = str(joins_value).strip()
        if joins_str:
            # Try to extract table aliases from simple join condition
            # Pattern: "o.customer_id = c.customer_id"
            match = re.search(r'(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)', joins_str)
            if match:
                left_alias, left_col, right_alias, right_col = match.groups()
                join_info = {
                    'left_table': left_alias,
                    'right_table': right_alias,
                    'left_column': left_col,
                    'right_column': right_col,
                    'join_type': 'JOIN',
                    'transformation': '',
                    'condition': joins_str,
                    'format': 'string'
                }
                
                logger.debug(f"Parsed string join: {join_info}")
                return join_info
            else:
                # Generic join condition
                return {
                    'left_table': 'unknown',
                    'right_table': 'unknown', 
                    'left_column': '',
                    'right_column': '',
                    'join_type': 'JOIN',
                    'transformation': '',
                    'condition': joins_str,
                    'format': 'string'
                }
                
    except Exception as e:
        logger.warning(f"Failed to parse joins column '{joins_value}': {e}")
        return None
    
    return None

def display_query_card(row, index: int):
    """Display a single query card with graceful missing data handling"""
    query = safe_get_value(row, 'query')
    description = safe_get_value(row, 'description')
    tables_raw = safe_get_value(row, 'table')
    joins_raw = safe_get_value(row, 'joins')
    
    # Parse tables and joins using new functions
    tables_list = parse_tables_column(tables_raw)
    join_info = parse_joins_column(joins_raw)
    
    # Create title based on available data
    if description:
        title = f"Query {index + 1}: {description[:60]}{'...' if len(description) > 60 else ''}"
    else:
        title = f"Query {index + 1}: {query[:40]}{'...' if len(query) > 40 else ''}"
    
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
        
        if join_info:
            st.markdown("**Join Information:**")
            
            # Display join details in a structured way
            if join_info['format'] == 'json':
                # Rich display for JSON format
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"- **Join Type:** {join_info['join_type']}")
                    st.markdown(f"- **Left Table:** {join_info['left_table']}")
                    st.markdown(f"- **Right Table:** {join_info['right_table']}")
                
                with col2:
                    if join_info['left_column'] and join_info['right_column']:
                        st.markdown(f"- **Left Column:** {join_info['left_column']}")
                        st.markdown(f"- **Right Column:** {join_info['right_column']}")
                
                if join_info['transformation']:
                    st.markdown(f"- **Transformation:** `{join_info['transformation']}`")
                else:
                    st.markdown(f"- **Condition:** `{join_info['condition']}`")
            else:
                # Simple display for string format
                st.markdown(f"- **Condition:** `{join_info['condition']}`")
                if join_info['left_table'] != 'unknown':
                    st.markdown(f"- **Tables:** {join_info['left_table']} ↔ {join_info['right_table']}")
            
            metadata_shown = True
        
        if not metadata_shown and not (description or tables_list or join_info):
            st.caption("_No additional metadata available_")

def analyze_joins(df: pd.DataFrame) -> Dict:
    """Analyze join patterns from the dataframe with enhanced JSON parsing"""
    join_analysis = {
        'relationships': [],
        'table_usage': defaultdict(int),
        'join_patterns': [],
        'join_types': defaultdict(int),
        'total_queries': len(df),
        'queries_with_joins': 0,
        'queries_with_descriptions': 0,
        'queries_with_tables': 0,
        'json_format_count': 0,
        'string_format_count': 0
    }
    
    for _, row in df.iterrows():
        query = safe_get_value(row, 'query')
        description = safe_get_value(row, 'description')
        tables_raw = safe_get_value(row, 'table')
        joins_raw = safe_get_value(row, 'joins')
        
        # Parse using new functions
        tables_list = parse_tables_column(tables_raw)
        join_info = parse_joins_column(joins_raw)
        
        # Count metadata availability
        if description:
            join_analysis['queries_with_descriptions'] += 1
        if tables_list:
            join_analysis['queries_with_tables'] += 1
        if join_info:
            join_analysis['queries_with_joins'] += 1
            
            # Track format types
            if join_info['format'] == 'json':
                join_analysis['json_format_count'] += 1
            else:
                join_analysis['string_format_count'] += 1
        
        # Process table usage
        for table in tables_list:
            if table:
                join_analysis['table_usage'][table] += 1
        
        # Process join relationships
        if join_info:
            # Track join type
            join_type = join_info.get('join_type', 'JOIN')
            join_analysis['join_types'][join_type] += 1
            
            # Store join pattern
            if join_info['transformation']:
                join_analysis['join_patterns'].append(join_info['transformation'])
            else:
                join_analysis['join_patterns'].append(join_info['condition'])
            
            # Create relationship entry
            relationship = {
                'left_table': join_info['left_table'],
                'right_table': join_info['right_table'],
                'condition': join_info['condition'],
                'join_type': join_type,
                'format': join_info['format']
            }
            
            # Add detailed information for JSON format
            if join_info['format'] == 'json':
                relationship.update({
                    'left_column': join_info.get('left_column', ''),
                    'right_column': join_info.get('right_column', ''),
                    'transformation': join_info.get('transformation', '')
                })
            
            join_analysis['relationships'].append(relationship)
    
    return join_analysis

def display_join_analysis(join_analysis: Dict):
    """Display enhanced join analysis with JSON format support"""
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
    
    # Format statistics (if there are joins)
    if join_analysis['queries_with_joins'] > 0:
        st.subheader("📋 Format Statistics")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("JSON Format", join_analysis['json_format_count'])
        
        with col2:
            st.metric("String Format", join_analysis['string_format_count'])
    
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
        
        # Enhanced graph visualization
        if GRAPHVIZ_AVAILABLE and len(join_analysis['relationships']) > 0:
            st.subheader("🌐 Table Relationship Graph")
            
            graph = graphviz.Graph(comment='Table Relationships')
            graph.attr(rankdir='TB', size='10,8')
            graph.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue')
            
            # Color map for different join types
            join_colors = {
                'LEFT JOIN': 'blue',
                'RIGHT JOIN': 'red', 
                'INNER JOIN': 'green',
                'FULL JOIN': 'orange',
                'JOIN': 'black'
            }
            
            # Add nodes and edges with enhanced styling
            tables_added = set()
            for rel in join_analysis['relationships']:
                left_table = rel['left_table']
                right_table = rel['right_table']
                join_type = rel.get('join_type', 'JOIN')
                
                # Skip unknown tables from string parsing
                if left_table == 'unknown' or right_table == 'unknown':
                    continue
                
                if left_table not in tables_added:
                    graph.node(left_table, left_table)
                    tables_added.add(left_table)
                
                if right_table not in tables_added:
                    graph.node(right_table, right_table)
                    tables_added.add(right_table)
                
                # Style edge based on join type
                edge_color = join_colors.get(join_type, 'black')
                edge_label = join_type
                
                # Add transformation info if available
                if rel.get('transformation') and rel['format'] == 'json':
                    # Truncate long transformations for display
                    transform = rel['transformation']
                    if len(transform) > 30:
                        transform = transform[:30] + '...'
                    edge_label = f"{join_type}\n{transform}"
                
                graph.edge(
                    left_table, 
                    right_table, 
                    label=edge_label,
                    color=edge_color,
                    fontsize='10'
                )
            
            try:
                if tables_added:  # Only show graph if we have valid tables
                    st.graphviz_chart(graph.source)
                else:
                    st.info("No valid table relationships found for graph visualization")
            except Exception as e:
                st.warning(f"Could not render graph: {e}")
    else:
        st.info("No join relationships found in the data")

def create_query_catalog_page(df: pd.DataFrame):
    """Create the query catalog page"""
    st.subheader("📚 Query Catalog")
    st.caption(f"Browse all {len(df)} SQL queries with their metadata")
    
    # Search/filter functionality
    search_term = st.text_input(
        "🔍 Search queries:", 
        placeholder="Search by query content, description, or tables..."
    )
    
    # Filter dataframe based on search
    filtered_df = df
    if search_term:
        search_lower = search_term.lower()
        
        # Enhanced search that includes parsed table and join data
        mask_list = []
        for idx, row in df.iterrows():
            match = False
            
            # Search in query
            query = safe_get_value(row, 'query')
            if search_lower in query.lower():
                match = True
            
            # Search in description
            description = safe_get_value(row, 'description')
            if search_lower in description.lower():
                match = True
            
            # Search in parsed tables
            tables_raw = safe_get_value(row, 'table')
            tables_list = parse_tables_column(tables_raw)
            for table in tables_list:
                if search_lower in table.lower():
                    match = True
                    break
            
            # Search in parsed joins
            joins_raw = safe_get_value(row, 'joins')
            join_info = parse_joins_column(joins_raw)
            if join_info:
                # Search in join details
                searchable_join_text = ' '.join([
                    join_info.get('left_table', ''),
                    join_info.get('right_table', ''),
                    join_info.get('left_column', ''),
                    join_info.get('right_column', ''),
                    join_info.get('join_type', ''),
                    join_info.get('condition', ''),
                    join_info.get('transformation', '')
                ]).lower()
                
                if search_lower in searchable_join_text:
                    match = True
            
            mask_list.append(match)
        
        # Apply the mask
        filtered_df = df[pd.Series(mask_list, index=df.index)]
        
        st.info(f"Found {len(filtered_df)} queries matching '{search_term}'")
    
    # Display join analysis
    join_analysis = analyze_joins(filtered_df)
    display_join_analysis(join_analysis)
    
    st.divider()
    
    # Display queries
    st.subheader(f"📋 Queries ({len(filtered_df)} total)")
    
    if len(filtered_df) == 0:
        st.warning("No queries found matching your search criteria")
        return
    
    # Display each query
    for index, (_, row) in enumerate(filtered_df.iterrows()):
        display_query_card(row, index)

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
            {total_tokens:,} tokens | {query_count} queries | 🏠 Ollama Phi3 (Free)
        </div>
        """, unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    # Header
    st.title("🛍️ Simple SQL RAG")
    st.caption("Ask questions about your SQL queries using pre-built vector search")
    
    # Load CSV data first (needed for both pages)
    if 'csv_data' not in st.session_state:
        csv_data = load_csv_data()
        if csv_data is not None:
            st.session_state.csv_data = csv_data
        else:
            st.error("Cannot proceed without CSV data")
            st.stop()
    
    # Sidebar for navigation and configuration
    with st.sidebar:
        st.header("📱 Navigation")
        
        # Page selection
        page = st.radio(
            "Select Page:",
            ["🔍 Query Search", "📚 Query Catalog"],
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
            
            # Search parameters
            st.subheader("🔍 Search Settings")
            k = st.slider("Top-K Results", 1, 10, 4, help="Number of relevant chunks to retrieve")
            
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
            placeholder="e.g., Which queries show customer spending analysis?"
        )
        
        if st.button("🔍 Search", type="primary") and query.strip():
            with st.spinner("Searching and generating answer..."):
                try:
                    # Call our simplified RAG function
                    result = answer_question_simple(
                        question=query,
                        vector_store=st.session_state.vector_store,
                        k=k
                    )
                    
                    if result:
                        answer, sources, token_usage = result
                        
                        # Track token usage
                        if token_usage:
                            st.session_state.token_usage.append(token_usage)
                        
                        # Display answer
                        st.subheader("📜 Answer")
                        st.write(answer)
                        
                        # Display token usage for this query
                        if token_usage:
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric(
                                    "🪙 Tokens Used", 
                                    f"{token_usage['total_tokens']:,}",
                                    f"In: {token_usage['prompt_tokens']:,} | Out: {token_usage['completion_tokens']:,}"
                                )
                            with col2:
                                st.metric("🏠 Model", "Ollama Phi3", "Free")
                        
                        # Display sources
                        if sources:
                            st.subheader("📂 Sources")
                            
                            for i, doc in enumerate(sources, 1):
                                with st.expander(f"Source {i}: {doc.metadata.get('source', 'Unknown')}"):
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
            st.markdown("""
            ### 💡 How to use:
            
            1. **First time setup:**
               ```bash
               python standalone_embedding_generator.py --csv "your_queries.csv"
               ```
            
            2. **Ask questions** about your SQL queries and get answers with source attribution
            
            3. **Adjust Top-K** in the sidebar to get more or fewer source documents
            
            ### 🚀 Performance Tips:
            - Pre-built vector stores load instantly
            - All processing runs locally with Ollama
            - GPU acceleration used if available during vector store creation
            """)
    
    else:
        # Query Catalog page
        create_query_catalog_page(st.session_state.csv_data)

if __name__ == "__main__":
    main()