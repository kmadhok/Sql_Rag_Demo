"""
Retail-SQL RAG – Streamlit front-end
Run with:
    streamlit run rag_app/app.py
"""

from __future__ import annotations

import pathlib
import sys
from typing import List, Dict
# from google.cloud import bigquery  # Commented out for local testing
import sqlparse
import streamlit as st
import pandas as pd
from functools import lru_cache
import json
import re
import os
import hashlib
import threading
import time
import logging

from collections import defaultdict
import graphviz
from rapidfuzz import fuzz
from dotenv import load_dotenv, find_dotenv
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS

# Interactive graph support
try:
    from pyvis.network import Network  # type: ignore
    import streamlit.components.v1 as components
except ImportError:  # graceful degradation if pyvis not installed yet
    Network = None

# Make sure the rag_app package itself is importable when script
# executed from project root (`streamlit run rag_app/app.py`)
APP_DIR = pathlib.Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))
    
# Define persistent paths
VECTOR_STORE_PATH = APP_DIR / "faiss_indices" 
EMBEDDING_STATUS_PATH = APP_DIR / "embedding_status.json"  # New status file path
QUERY_CSV_PATH = APP_DIR.parent.parent / "archive" / "sample_queries.csv"  # Path to sample queries
os.makedirs(VECTOR_STORE_PATH, exist_ok=True)

from simple_rag import answer_question  # noqa: E402  (after sys.path tweak)
# from actions import append_to_host_table  # Commented out for local testing
from smart_embedding_processor import SmartEmbeddingProcessor
from windows_embedding_processor import get_embedding_processor
from data_source_manager import DataSourceManager, load_data_with_fallback
from actions.rebuild_embeddings import force_rebuild_embeddings
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize embedding processor with automatic Windows detection (using st.cache_resource for persistence)
@st.cache_resource
def get_smart_processor():
    """Get or create the cross-platform embedding processor singleton"""
    import platform
    from pathlib import Path
    
    if platform.system() == 'Windows':
        # Use Windows-compatible processor with adapter for interface compatibility
        logger.info("🖥️ Windows system detected - using compatible embedding processor")
        
        # Create a Windows processor adapter that matches SmartEmbeddingProcessor interface
        class WindowsProcessorAdapter:
            def __init__(self, vector_store_path, status_file_path):
                self.vector_store_path = Path(vector_store_path)
                self.status_file_path = Path(status_file_path)
                self.windows_processor = get_embedding_processor(
                    initial_batch_size=100,
                    chunk_size=1000,
                    chunk_overlap=150
                )
            
            def load_existing_vector_store(self):
                """Load existing vector store if available"""
                # Check for existing FAISS indices in the directory
                for index_dir in self.vector_store_path.glob("index_*"):
                    if index_dir.is_dir():
                        try:
                            from langchain_ollama import OllamaEmbeddings
                            embeddings = OllamaEmbeddings(model="nomic-embed-text")
                            vector_store = FAISS.load_local(
                                str(index_dir), 
                                embeddings, 
                                allow_dangerous_deserialization=True
                            )
                            logger.info(f"✅ Loaded existing Windows vector store from {index_dir}")
                            return vector_store
                        except Exception as e:
                            logger.warning(f"Could not load existing store: {e}")
                return None
            
            def process_dataframe(self, df, source_name, source_info, initial_batch_size=100):
                """Process dataframe with Windows compatibility"""
                def progress_callback(message):
                    logger.info(message)
                
                vector_store = self.windows_processor.process_embeddings(
                    df, source_name, source_info, progress_callback
                )
                
                # Return stats compatible with original interface
                stats = {
                    'cache_hit': False,  # Windows processor always processes
                    'new_documents': len(df),
                    'total_documents': len(vector_store.docstore._dict),
                    'processing_time': 0  # Would need to track separately
                }
                
                return vector_store, stats
        
        return WindowsProcessorAdapter(VECTOR_STORE_PATH, EMBEDDING_STATUS_PATH)
    else:
        # Use original processor for non-Windows systems
        logger.info("🐧 Non-Windows system detected - using standard embedding processor")
        return SmartEmbeddingProcessor(VECTOR_STORE_PATH, EMBEDDING_STATUS_PATH)

# Load environment variables from any .env up the tree
load_dotenv(find_dotenv(), override=False)

# --------------------------------------------------------------------------- #
#  Token tracking and cost calculation utilities
# --------------------------------------------------------------------------- #

# Token usage tracking for local Ollama - no costs involved

def get_session_token_stats():
    """Get cumulative token statistics for the session."""
    if 'token_usage' not in st.session_state:
        st.session_state.token_usage = []
    
    total_prompt = sum(usage.get('prompt_tokens', 0) for usage in st.session_state.token_usage)
    total_completion = sum(usage.get('completion_tokens', 0) for usage in st.session_state.token_usage)
    total_tokens = total_prompt + total_completion
    
    return {
        'total_tokens': total_tokens,
        'prompt_tokens': total_prompt,
        'completion_tokens': total_completion,
        'query_count': len(st.session_state.token_usage)
    }

def add_token_usage(token_usage: dict):
    """Add token usage to session state tracking."""
    if 'token_usage' not in st.session_state:
        st.session_state.token_usage = []
    st.session_state.token_usage.append(token_usage)

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

def display_session_usage():
    """Displays the session token usage information."""
    stats = get_session_token_stats()
    if stats['query_count'] > 0:
        st.markdown("""
        <style>
            .usage-container {
                background-color: #262730;
                color: white;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-around;
                align-items: center;
                flex-wrap: wrap;
            }
            .usage-stat {
                font-size: 14px;
                text-align: center;
                margin: 5px 10px;
            }
            .usage-label {
                font-weight: bold;
                font-size: 16px;
            }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="usage-container">
            <span class="usage-label">📊 Session Usage</span>
            <span class="usage-stat">🪙 Tokens: {stats['total_tokens']:,}</span>
            <span class="usage-stat">💬 Queries: {stats['query_count']}</span>
            <span class="usage-stat">🏠 Ollama Phi3 Model</span>
        </div>
        """, unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
#  Page config & small helpers
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Retail-SQL RAG", layout="wide")

# --------------------------------------------------------------------------- #
#  Top-level navigation (Chat vs. Catalog)
# --------------------------------------------------------------------------- #

PAGE = st.sidebar.radio("Navigation", ["🔎 Query Search", "📚 Browse Queries"], key="nav")

# Load query data using smart data source manager
if 'query_df' not in st.session_state or 'data_source_info' not in st.session_state:
    try:
        # Create data source with fallback
        csv_path = '/Users/kanumadhok/Sql_Rag_Demo/SQL_RAG/queries_with_descriptions (1).csv'
        
        # Try to detect BigQuery first, fall back to CSV
        try:
            data_source = DataSourceManager.auto_detect_source(
                csv_path=csv_path,
                bigquery_project=os.getenv('BIGQUERY_PROJECT'),  # From environment
                prefer_bigquery=False  # Prefer CSV for now, change to True for production
            )
        except Exception:
            # Direct CSV fallback
            data_source = DataSourceManager.create_csv_source(csv_path)
        
        # Load data with fallback
        st.session_state.query_df, source_info = load_data_with_fallback(
            data_source, 
            fallback_csv_path=csv_path
        )
        st.session_state.data_source_info = source_info
        
        # Debug info
        st.info(f"📊 Loaded {len(st.session_state.query_df)} rows from {data_source.get_source_name()}")
        st.caption(f"Columns: {list(st.session_state.query_df.columns)}")
        
    except Exception as e:
        st.error(f"❌ Failed to load data: {e}")
        # Fallback to sample data
        st.session_state.query_df = pd.DataFrame({
            'query': ['SELECT 1 as test'],
            'description': ['Test query']
        })
        st.session_state.data_source_info = "fallback_sample_data"
        st.warning("Using fallback sample data")
    # pd.DataFrame({
    #     'query': [
    #         'SELECT customer_id, SUM(amount) as total_spent FROM transactions WHERE date >= "2024-01-01" GROUP BY customer_id ORDER BY total_spent DESC',
    #         'SELECT p.product_name, COUNT(*) as purchase_count FROM products p JOIN order_items oi ON p.id = oi.product_id GROUP BY p.product_name',
    #         'WITH monthly_sales AS (SELECT DATE_TRUNC(date, MONTH) as month, SUM(amount) as sales FROM transactions GROUP BY month) SELECT * FROM monthly_sales ORDER BY month'
    #     ],
    #     'description': [
    #         'Customer spending analysis showing total amount spent by each customer since January 2024',
    #         'Product popularity report counting how many times each product has been purchased', 
    #         'Monthly sales trend analysis using window functions to show sales by month'
    #     ]
    # })

# Shared header
st.title("🛍️  Retail SQL Knowledge Base")
st.caption("📄 Local Test Queries • Auto-generated descriptions • Ollama Phi3 model")

# --- Smart vector store management with incremental updates ---
if 'vector_store' not in st.session_state:
    try:
        processor = get_smart_processor()  # Already cached
        
        # Check if existing vector store can be loaded
        existing_vector_store = processor.load_existing_vector_store()
        
        if existing_vector_store:
            # Check if data has changed and needs incremental update
            st.info("🔍 Checking for data changes...")
            
            try:
                # Process with incremental updates (fast if no changes)
                with st.spinner("Processing embeddings (incremental updates enabled)..."):
                    start_time = time.time()
                    vector_store, stats = processor.process_dataframe(
                        st.session_state.query_df,
                        source_name="query_data",
                        source_info=st.session_state.data_source_info,
                        initial_batch_size=100
                    )
                    elapsed = time.time() - start_time
                    
                    st.session_state.vector_store = vector_store
                    
                    # Show processing stats
                    if stats.get('cache_hit'):
                        st.success("✅ Data unchanged - loaded existing embeddings!")
                    else:
                        st.success(f"✅ Processed {stats['new_documents']} documents in {stats['processing_time']:.1f}s")
                        if stats.get('background_time', 0) > 0:
                            st.info(f"⚡ Background processing: {stats['background_time']:.1f}s")
                        
            except Exception as e:
                st.error(f"❌ Error during smart processing: {e}")
                logger.error(f"Smart processing error: {e}", exc_info=True)
                # Fallback to existing vector store
                st.session_state.vector_store = existing_vector_store
                st.warning("⚠️ Using existing vector store due to processing error")
                
        else:
            # No existing vector store - create new one
            st.info(f"🔄 Creating new embeddings for {len(st.session_state.query_df)} queries...")
            
            # Check Ollama availability first
            try:
                from actions.ollama_llm_client import check_ollama_availability
                available, status_msg = check_ollama_availability()
                if not available:
                    st.error(f"❌ Ollama not available: {status_msg}")
                    st.stop()
                else:
                    st.info(f"✅ Ollama status: {status_msg}")
            except Exception as e:
                st.warning(f"⚠️ Could not check Ollama status: {e}")
            
            with st.spinner("Processing embeddings with smart batching..."):
                try:
                    start_time = time.time()
                    vector_store, stats = processor.process_dataframe(
                        st.session_state.query_df,
                        source_name="query_data", 
                        source_info=st.session_state.data_source_info,
                        initial_batch_size=100
                    )
                    elapsed = time.time() - start_time
                    st.session_state.vector_store = vector_store
                    
                    st.success(f"✅ Created embeddings for {stats['total_processed']} documents!")
                    st.info(f"⏱️ Initial batch: {stats['initial_batch_time']:.1f}s | Total: {stats['processing_time']:.1f}s")
                    
                except Exception as e:
                    st.error(f"❌ Error creating embeddings: {e}")
                    logger.error(f"Embedding creation error: {e}", exc_info=True)
                    st.stop()
            
            st.success("✅ Ready to use! Background processing continues...")
            logger.info("Initial batch processed, background processing started")
                
    except Exception as e:
        logger.error(f"Failed to load knowledge base: {str(e)}", exc_info=True)
        st.error(f"Failed to load knowledge base: {str(e)}")
        st.stop()
        
# Show processing status from smart processor
if 'vector_store' in st.session_state:
    try:
        processor = get_smart_processor()
        status = processor.get_processing_status()
        
        # Show data source info
        if 'data_source_info' in st.session_state:
            st.caption(f"📊 Data source: {st.session_state.data_source_info}")
        
        # Show processing summary
        total_processed = status.get('total_processed', 0)
        if total_processed > 0:
            st.caption(f"✅ {total_processed:,} documents embedded | Last updated: {status.get('last_updated', 'unknown')}")
            
    except Exception as e:
        logger.error(f"Error reading smart processor status: {e}", exc_info=True)
# ---------------------------------------------------------

# Token counter in top right corner is being moved below

# Note: Descriptions are now stored directly in CSV file, no separate cache needed

def _format_snippet(text: str, suffix: str) -> str:
    """Prettify SQL snippets – leaves Python untouched."""
    if suffix.endswith(".sql"):
        return sqlparse.format(text, reindent=True, keyword_case="upper")
    return text


# --------------------------------------------------------------------------- #
#  Sidebar – parameters
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("⚙️  Settings")
    
    # Add Gemini mode toggle
    gemini_mode = st.checkbox("🔥 Gemini Mode", value=False, 
                             help="Utilize Gemini's 1M context window with many more chunks")
    
    if gemini_mode:
        k = st.slider("Top-K chunks", min_value=10, max_value=200, value=100,
                     help="Gemini can handle 100+ chunks efficiently")
        st.success("🚀 Gemini Mode: Using large context window")
    else:
        k = st.slider("Top-K chunks", min_value=1, max_value=20, value=4,
                     help="Conservative mode for smaller models")
    
    st.markdown(
        """
        _Tip: Gemini Mode leverages the 1M token context window for comprehensive answers._
        """
    )
    
    # Vector store controls
    st.divider()
    st.header("🗃️ Vector Database")
    
    if st.button("🔄 Rebuild Vector Store", help="Force rebuild the vector embeddings database"):
        with st.spinner("Rebuilding vector store..."):
            try:
                # Clear existing files
                force_rebuild_embeddings(VECTOR_STORE_PATH, EMBEDDING_STATUS_PATH)
                
                # Clear from session state and cache
                if 'vector_store' in st.session_state:
                    del st.session_state.vector_store
                    
                # Clear cached processor to force reinitialization
                st.cache_resource.clear()
                
                # Force rebuild with smart processor
                processor = SmartEmbeddingProcessor(VECTOR_STORE_PATH, EMBEDDING_STATUS_PATH)
                vector_store, stats = processor.process_dataframe(
                    st.session_state.query_df,
                    source_name="query_data",
                    source_info=st.session_state.get('data_source_info', ''),
                    force_rebuild=True
                )
                st.session_state.vector_store = vector_store
                
                st.success(f"✅ Rebuilt vector store with {stats['total_processed']} documents!")
                st.info(f"⏱️ Processing time: {stats['processing_time']:.1f}s")
                
            except Exception as e:
                st.error(f"❌ Error rebuilding vector store: {e}")
                logger.error(f"Rebuild error: {e}", exc_info=True)
    
    # Token usage controls
    st.divider()
    st.header("📊 Token Tracking")
    
    if st.button("🔄 Reset Token Counter"):
        st.session_state.token_usage = []
        st.rerun()
    
    # Show model information
    with st.expander("🏠 Ollama Model Info"):
        st.markdown("""
        **Current Model:** Phi3:3.8B via Ollama
        
        - **Inference:** Local Ollama service
        - **Cost:** Free (no API charges)
        - **Privacy:** All processing stays local
        - **Performance:** Optimized for local hardware
        
        *Token counts are estimated based on text length.*
        """)
    
    # Smart Processor Status Info  
    with st.expander("🔄 Smart Embedding Status"):
        try:
            processor = get_smart_processor()
            status = processor.get_processing_status()
            
            total_processed = status.get('total_processed', 0)
            processed_sources = status.get('processed_sources', [])
            
            if total_processed > 0:
                st.success(f"✅ {total_processed:,} documents embedded")
                
                # Show data sources
                if processed_sources:
                    st.markdown("**Data Sources:**")
                    for source in processed_sources[-3:]:  # Show last 3 sources
                        source_name = source.get('name', 'unknown')
                        doc_count = source.get('document_count', 0)
                        last_proc = source.get('last_processed', '')
                        
                        try:
                            from datetime import datetime
                            time_str = datetime.fromisoformat(last_proc).strftime('%Y-%m-%d %H:%M')
                        except:
                            time_str = last_proc[:16] if last_proc else 'unknown'
                        
                        st.caption(f"• {source_name}: {doc_count:,} docs ({time_str})")
                
                # Show vector store status
                vector_exists = status.get('vector_store_exists', False)
                if vector_exists:
                    st.info("🗃️ Vector store ready for queries")
                else:
                    st.warning("⚠️ Vector store not found")
                    
            else:
                st.info("No embeddings processed yet")
                
            # Show last update
            last_updated = status.get('last_updated', '')
            if last_updated:
                try:
                    from datetime import datetime
                    update_time = datetime.fromisoformat(last_updated)
                    st.caption(f"Last updated: {update_time.strftime('%H:%M:%S')}")
                except:
                    pass
                    
        except Exception as e:
            st.error(f"Error reading smart processor status: {e}")

    # Show session statistics
    if 'token_usage' in st.session_state and st.session_state.token_usage:
        st.divider()
        stats = get_session_token_stats()
        st.metric("Total Tokens", f"{stats['total_tokens']:,}")
        st.metric("Total Queries", stats['query_count'])


# --------------------------------------------------------------------------- #
#  Main interaction
# --------------------------------------------------------------------------- #
if PAGE == "🔎 Query Search":
    query = st.text_input("Ask a question about the retail codebase:", placeholder="e.g. Which query joins inventory with sales?")

    display_session_usage()

    if st.button("🔍  Ask") and query.strip():
        with st.spinner("Thinking…"):
            try:
                # Pass the cached vector store to the answer function
                answer, docs, token_usage = answer_question(
                    query,
                    vector_store=st.session_state.vector_store,
                    k=k,
                    return_docs=True,
                    return_tokens=True,
                    gemini_mode=gemini_mode
                )
                
                # Track token usage
                if token_usage:
                    add_token_usage(token_usage)
                    
            except Exception as exc:  # catch Ollama or other errors
                st.error(f"❌ Ollama Phi3 call failed: {exc}")
                st.stop()

        # -------- Answer
        st.subheader("📜 Answer")
        st.write(answer)
        
        # -------- Context Utilization Metrics
        if docs:
            context_stats = calculate_context_utilization(docs, query)
            
            # Display context utilization with color-coded progress bar
            utilization = context_stats['utilization_percent']
            
            # Color coding based on utilization
            if utilization < 10:
                color = "🔴"  # Very low utilization
                status = "Low utilization - consider increasing K for better results"
            elif utilization < 50:
                color = "🟡"  # Moderate utilization
                status = "Moderate utilization - could use more context"
            else:
                color = "🟢"  # Good utilization
                status = "Good context utilization"
            
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
                    help="Number of relevant chunks retrieved from vector store"
                )
            
            with col3:
                if gemini_mode:
                    remaining_tokens = 1000000 - context_stats['total_input_tokens']
                    st.metric(
                        label="🚀 Remaining Capacity",
                        value=f"{remaining_tokens:,}",
                        delta="tokens available",
                        help="Additional tokens available in Gemini's context window"
                    )
                else:
                    st.metric(
                        label="🏠 Local Model",
                        value="Ollama Phi3",
                        delta="No token limits",
                        help="Using local model with flexible context"
                    )
            
            st.caption(f"💡 {status}")
        
        # -------- Token Usage for this query (original metrics)
        if token_usage:
            st.divider()
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    label="🪙 Response Tokens",
                    value=f"{token_usage['total_tokens']:,}",
                    delta=f"In: {token_usage['prompt_tokens']:,} | Out: {token_usage['completion_tokens']:,}"
                )
            
            with col2:
                st.metric(
                    label="🏠 Ollama Phi3",
                    value="Free",
                    delta="No API costs"
                )

        # -------- Sources (as tabs)
        st.divider()
        st.subheader("📂 Sources")

        if not docs:
            st.info("No supporting chunks returned.")
        else:
            # Group retrieved chunks by their source file
            grouped: Dict[str, List] = defaultdict(list)
            order: List[str] = []  # preserve retrieval order for tab display
            for d in docs:
                src = d.metadata["source"]
                if src not in grouped:
                    order.append(src)
                grouped[src].append(d)

            tab_labels = [f"{path}  ▸  {len(grouped[path])} chunk{'s' if len(grouped[path])>1 else ''}" for path in order]
            tab_objs = st.tabs(tab_labels)

            for path, tab in zip(order, tab_objs):
                doc_list = grouped[path]
                with tab:
                    st.markdown(f"**File:** `{path}` – retrieved **{len(doc_list)}** chunk(s)")

                    # show each individual chunk first (for pinpointing where the answer came from)
                    for d in doc_list:
                        with st.expander(f"Chunk {d.metadata['chunk']}"):
                            snippet = _format_snippet(d.page_content, path)
                            lang = "sql" if path.endswith(".sql") else "python"
                            st.code(snippet, language=lang)

                    # For CSV mode, we don't have full files to display
                    full_text = ""

                    if full_text:
                        with st.expander("📄 Show full query / file"):
                            lang = "sql" if path.endswith(".sql") else "python"
                            st.code(_format_snippet(full_text, path), language=lang)

    else:
        st.markdown(
            """
            <br/>
            ℹ️ Enter a question and click **Ask** to see the model's answer along
            with every retrieved code/SQL chunk.
            """,
            unsafe_allow_html=True,
        )

# --------------------------------------------------------------------------- #
#  Catalog page – browse all queries with auto-generated descriptions
# --------------------------------------------------------------------------- #
else:

    st.subheader("📚 Browse All Queries")

    # ------------------------------------------------------
    # 1. Build join map (table1 -> table2) from all SQL files
    # ------------------------------------------------------

    def _scan_joins(sql_text: str):
        """Return list of dicts describing every sequential JOIN.

        Columns returned:
            • Left Table – table (or alias) on the left side of the JOIN clause
            • Right Table – token that follows JOIN
            • On – join predicate (trimmed)
            • Alias L / Alias R – best-effort aliases from first equality in ON
        """

        # Find the first table after FROM to seed the left-hand side
        m_from = re.search(r"FROM\s+([`\"\w\.]+)", sql_text, flags=re.IGNORECASE)
        current_left = m_from.group(1).strip("`\"") if m_from else "?"

        join_regex = re.compile(
            r"(?:LEFT|RIGHT|FULL|INNER|OUTER|CROSS)?\s*JOIN\s+([`\"\w\.]+)(?:\s+AS\s+\w+|\s+\w+)?\s+ON\s+(.+?)(?=\b(?:LEFT|RIGHT|FULL|INNER|OUTER|CROSS)?\s*JOIN\b|\bWHERE\b|\bGROUP\s+BY\b|\bHAVING\b|\bORDER\s+BY\b|\bLIMIT\b|;|$)",
            flags=re.IGNORECASE | re.DOTALL,
        )

        results = []
        for m in join_regex.finditer(sql_text):
            right_tbl = m.group(1).strip("`\"")
            on_raw = re.sub(r"\s+", " ", m.group(2).strip())  # collapse whitespace
            on_trim = on_raw if len(on_raw) <= 160 else on_raw[:157] + "…"

            # Pull aliases/tables from equality
            left_alias = right_alias = "?"
            m_eq = re.search(r"([a-zA-Z_][\w]*)\.\w+\s*=\s*([a-zA-Z_][\w]*)\.\w+", on_raw)
            if m_eq:
                left_alias, right_alias = m_eq.group(1), m_eq.group(2)

            results.append({
                "Left Table": current_left,
                "Right Table": right_tbl,
                "Alias L": left_alias,
                "Alias R": right_alias,
                "On": on_trim,
            })

            # Update current_left for chained JOINs
            current_left = right_tbl

        return results

    join_rows = []  # list of dict rows
    
    # Analyze joins from queries in DataFrame
    try:
        df = st.session_state.query_df
        
        if 'query' in df.columns:
            for idx, row in df.iterrows():
                query_text = row['query']
                if not query_text or pd.isna(query_text):
                    continue
                
                # Apply join analysis to each query
                joins = _scan_joins(str(query_text))
                if joins:  # Only add if joins were found
                    for j in joins:
                        join_row = {"File": f"Query {idx + 1}"}
                        join_row.update(j)
                        join_rows.append(join_row)
    except Exception as e:
        st.error(f"Error analyzing joins from DataFrame: {e}")
        join_rows = []

    if join_rows:
        df_join = st.session_state.get("_df_join")
        if df_join is None:
            import pandas as pd
            df_join = pd.DataFrame(join_rows)
            st.session_state["_df_join"] = df_join

        st.subheader("🧩 Join Map (detected via regex)")

        # ---------- Faceted Filters ---------- #
        table_cols = [c for c in df_join.columns if c in ("Left Table", "Right Table", "Alias L", "Alias R")]

        # Gather every distinct, non-null alias / table name for the facet selector
        all_tables = sorted({
            str(v)
            for col in table_cols
            for v in df_join[col].unique()
            if v and v != "?" and v != "nan"
        })
        sel_tables = st.multiselect("Filter by table(s):", options=all_tables)

        df_view = df_join
        if sel_tables:
            # keep rows where any of the table/alias columns intersects with the selection
            mask = df_view[table_cols].apply(lambda r: any(t in sel_tables for t in r), axis=1)
            df_view = df_view[mask]

        st.dataframe(df_view, use_container_width=True, hide_index=True)

        # ---------- Graph View ---------- #
        show_graph = st.checkbox("Show join graph", value=False)
        if show_graph:
            if Network is None:
                st.info("pyvis not installed – falling back to static Graphviz diagram.")
                g = graphviz.Graph()
                for _, row in df_view.iterrows():
                    g.edge(row["Left Table"], row["Right Table"], label=row["On"])
                st.graphviz_chart(g)
            else:
                # Build interactive network
                net = Network(height="600px", width="100%", directed=False, bgcolor="#ffffff")
                # Add nodes with consistent set
                nodes_added = set()
                for _, r in df_view.iterrows():
                    for tbl in (r["Left Table"], r["Right Table"]):
                        if tbl not in nodes_added:
                            net.add_node(tbl, label=tbl, title=tbl)
                            nodes_added.add(tbl)
                    net.add_edge(r["Left Table"], r["Right Table"], title=r["On"])

                net.toggle_physics(True)

                # Generate and display inside Streamlit
                html = net.generate_html(notebook=False)
                components.html(html, height=650, scrolling=True)

        # ---------- Transformation Overview ---------- #
        def _scan_transforms(sql_text: str):
            """Return transformation keywords present in the SQL text."""
            patterns = {
                "CAST": r"\bCAST\s*\(",
                "COALESCE": r"\bCOALESCE\s*\(",
                "NULLIF": r"\bNULLIF\s*\(",
                "REGEXP_REPLACE": r"\bREGEXP_REPLACE\s*\(",
                "REGEXP_LIKE": r"\bREGEXP_LIKE\s*\(",
                "REGEXP": r"\bREGEXP\b",
                "SUBSTRING": r"\bSUBSTRING\s*\(",
                "CONCAT": r"\bCONCAT\s*\(",
                "TRIM": r"\bTRIM\s*\(",
                "UPPER": r"\bUPPER\s*\(",
                "LOWER": r"\bLOWER\s*\(",
                "DATE_TRUNC": r"\bDATE_TRUNC\s*\(",
                "DATE_ADD": r"\bDATE_ADD\s*\(",
                "DATE_DIFF": r"\bDATE_DIFF\s*\(",
                "ROUND": r"\bROUND\s*\(",
            }
            return [
                name for name, pat in patterns.items()
                if re.search(pat, sql_text, flags=re.IGNORECASE)
            ]

        # No transformation analysis for CSV mode

    st.divider()

    # ------------------------------------------------------
    # Full-text search over all SQL / Python chunks with FAISS
    # ------------------------------------------------------

    search_query = st.text_input("🔍 Full-text search across codebase", key="global_search")
    if search_query:
        vs = st.session_state.vector_store # Use cached vector store
        hits = vs.similarity_search(search_query, k=5)
        for doc in hits:
            if fuzz.partial_ratio(search_query.lower(), doc.page_content.lower()) < 40:
                continue  # rough relevance filter
            st.markdown(f"**File:** `{doc.metadata['source']}` – chunk {doc.metadata['chunk']}")
            highlighted = re.sub(rf"({re.escape(search_query)})", r"**\1**", doc.page_content, flags=re.IGNORECASE)
            st.write(highlighted)
            st.markdown("---")

    # ------------------------------------------------------
    # Continue with description listing
    # ------------------------------------------------------

    # Show queries from DataFrame stored in session state
    st.subheader("📊 Local Test Queries")
    
    try:
        # Use DataFrame from session state
        import pandas as pd
        df = st.session_state.query_df
        
        if 'query' in df.columns:
            for idx, row in df.iterrows():
                query_text = row['query']
                if not query_text or pd.isna(query_text):
                    continue
                    
                # Create title using description or row number
                if 'description' in df.columns and not pd.isna(row.get('description')) and row.get('description'):
                    description = str(row['description'])
                    # Use first 60 characters of description as title
                    title = f"Query {idx + 1}: {description[:60]}{'...' if len(description) > 60 else ''}"
                else:
                    title = f"Query {idx + 1} (no description)"
                
                with st.expander(title):
                    # Show description prominently if available
                    if 'description' in df.columns and not pd.isna(row.get('description')) and row.get('description'):
                        st.markdown(f"**Description:** {row['description']}")
                        st.divider()
                    
                    # Show other metadata if available
                    metadata_cols = [col for col in df.columns if col not in ['query', 'description']]
                    if metadata_cols:
                        st.markdown("**Additional Metadata:**")
                        for col in metadata_cols:
                            if not pd.isna(row.get(col)) and row.get(col):
                                st.markdown(f"- **{col}**: {row[col]}")
                        st.divider()
                    
                    # Show the query
                    st.markdown("**SQL Query:**")
                    st.code(_format_snippet(str(query_text), "query.sql"), language="sql")
        else:
            st.error("CSV file must contain a 'query' column")
            
    except Exception as e:
        st.error(f"Error reading CSV: {e}")