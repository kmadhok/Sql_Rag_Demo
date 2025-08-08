"""
Retail-SQL RAG – Streamlit front-end
Run with:
    streamlit run rag_app/app.py
"""

from __future__ import annotations

import pathlib
import sys
from typing import List, Dict
from google.cloud import bigquery
import sqlparse
import streamlit as st
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
from actions import build_or_load_vector_store, append_to_host_table
from actions.progressive_embeddings import build_progressive_vector_store
from actions.embedding_manager import EmbeddingManager
from actions import initialize_vector_store_with_background_processing
from actions.rebuild_embeddings import force_rebuild_embeddings
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize embedding manager once (using st.cache_resource for persistence)
@st.cache_resource
def get_embedding_manager():
    """Get or create the embedding manager singleton"""
    return EmbeddingManager(VECTOR_STORE_PATH, EMBEDDING_STATUS_PATH)

@st.cache_resource
def get_vector_store_with_background_processing(_query_df, csv_file_path=None):
    """
    Get or initialize the vector store with background processing for improved performance.
    This function will:
    1. Load the existing vector store if available
    2. If not available, process an initial batch quickly (first 100 queries)
    3. Process the remaining queries in the background using ThreadPoolExecutor
    
    Args:
        _query_df: DataFrame containing queries (not used if vector store exists)
        csv_file_path: Optional path to CSV file
    
    Returns:
        FAISS vector store and background thread if processing is ongoing
    """
    # Check if vector store exists
    vector_store_path = str(VECTOR_STORE_PATH)
    vector_store_dir = os.path.dirname(vector_store_path)
    
    if os.path.exists(vector_store_path):
        # Load existing vector store
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vector_store = FAISS.load_local(vector_store_path, embeddings)
        return vector_store, None
    
    # Vector store doesn't exist - process data with parallel processing
    # First batch for immediate results + background processing for the rest
    return initialize_vector_store_with_background_processing(
        csv_file_path=csv_file_path,
        index_dir=vector_store_dir,
        initial_batch_size=100,
        max_workers=4,
        batch_size=25,
        status_file_path=str(EMBEDDING_STATUS_PATH)
    )
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
            <span class="usage-stat">🏠 Local Phi3 Model</span>
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

# Load query data directly from BigQuery into session state
if 'query_df' not in st.session_state:
    with st.spinner("Loading queries from BigQuery..."):
        bq_client = bigquery.Client(project='wmt-dv-bq-analytics')
        st.session_state.query_df = append_to_host_table(bq_client)

# Shared header
st.title("🛍️  Retail SQL Knowledge Base")
st.caption("📄 BigQuery Queries • Auto-generated descriptions • Local Phi3 model")

# --- Manage and cache the vector store in session state ---
if 'vector_store' not in st.session_state:
    try:
        # Use the new efficient approach with parallel processing
        csv_file_path = str(QUERY_CSV_PATH)
        
        with st.spinner("🔄 Loading or building vector store..."):
            vector_store, background_thread = get_vector_store_with_background_processing(
                st.session_state.query_df,
                csv_file_path=csv_file_path
            )
            
            st.session_state.vector_store = vector_store
            st.session_state.background_processing = background_thread is not None
            
            if background_thread:
                st.info("✅ Initial batch processed! Background processing ongoing...")
                logger.info("Initial batch processed, background processing started")
            else:
                st.success("✅ Loaded existing vector store!")
                logger.info("Loaded existing vector store")
                
    except Exception as e:
        logger.error(f"Failed to load knowledge base: {str(e)}", exc_info=True)
        st.error(f"Failed to load knowledge base: {str(e)}")
        st.stop()
        
# Show progress indicator based on embedding status file
if 'background_processing' in st.session_state and st.session_state.background_processing:
    # Check the status file directly
    if os.path.exists(EMBEDDING_STATUS_PATH):
        try:
            with open(EMBEDDING_STATUS_PATH, 'r') as f:
                status = json.load(f)
                
                if not status["is_complete"] and status["background_task_running"]:
                    # Calculate progress percentage
                    total = max(1, status["total_queries"])
                    processed = status["processed_queries"]
                    progress_pct = min(1.0, processed / total)
                    
                    # Display progress bar
                    st.progress(progress_pct, text=f"Processing embeddings: {processed:,}/{total:,} queries")
                    st.caption(f"⚡ Background embedding in progress - you can still use the app while this completes")
        except Exception as e:
            logger.error(f"Error reading status file: {e}", exc_info=True)
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
    k = st.slider("Top-K chunks", min_value=1, max_value=10, value=4)
    st.markdown(
        """
        _Tip: larger K means more context but slightly slower & wordier answers._
        """
    )
    
    # Vector store controls
    st.divider()
    st.header("🗃️ Vector Database")
    
    if st.button("🔄 Rebuild Vector Store", help="Force rebuild the vector embeddings database"):
        with st.spinner("Clearing existing vector store..."):
            # Force rebuild by clearing files and status
            force_rebuild_embeddings(VECTOR_STORE_PATH, EMBEDDING_STATUS_PATH)
            
            # Clear from session state to trigger rebuild
            if 'vector_store' in st.session_state:
                del st.session_state.vector_store
        
        st.success("Vector store cleared! Rebuilding on next refresh...")
        time.sleep(1)  # Brief pause to show the message
        st.rerun()  # Trigger app rerun to rebuild vector store
    
    # Token usage controls
    st.divider()
    st.header("📊 Token Tracking")
    
    if st.button("🔄 Reset Token Counter"):
        st.session_state.token_usage = []
        st.rerun()
    
    # Show model information
    with st.expander("🏠 Local Model Info"):
        st.markdown("""
        **Current Model:** Phi3 (3.8B parameters)
        
        - **Inference:** Local via Ollama
        - **Cost:** Free (no API charges)
        - **Privacy:** All processing stays local
        
        *Token counts are estimated based on text length.*
        """)
    
    # Embedding Status Info
    with st.expander("🔄 Embedding Status"):
        # Check the status file directly
        if os.path.exists(EMBEDDING_STATUS_PATH):
            try:
                with open(EMBEDDING_STATUS_PATH, 'r') as f:
                    status = json.load(f)
                    
                    if status["is_complete"]:
                        st.success(f"✅ All {status['total_queries']:,} queries embedded")
                    elif status["background_task_running"]:
                        progress = status["processed_queries"] / max(1, status["total_queries"])
                        st.progress(progress, text=f"{status['processed_queries']:,}/{status['total_queries']:,}")
                        st.info(f"⏳ Background processing active")
                        
                        # Show last update time
                        if "last_updated" in status:
                            from datetime import datetime
                            try:
                                last_update = datetime.fromisoformat(status["last_updated"])
                                st.caption(f"Last updated: {last_update.strftime('%H:%M:%S')}")
                            except (ValueError, TypeError):
                                pass
                    else:
                        if "error" in status and status["error"]:
                            st.error(f"❌ Error: {status['error']}")
                        else:
                            st.warning(f"⚠️ Processing paused or incomplete")
                            st.caption(f"Processed {status['processed_queries']:,}/{status['total_queries']:,} queries")
            except Exception as e:
                st.error(f"Error reading status file: {e}")
        else:
            st.info("No embedding status information available.")

    # Show session statistics
    if 'token_usage' in st.session_state and st.session_state.token_usage:
        st.divider()
        stats = get_session_token_stats()
        st.metric("Total Tokens", f"{stats['total_tokens']:,}")
        st.metric("Total Queries", stats['query_count'])

# Show progress indicator for background embedding generation
if 'embedding_status' in st.session_state:
    status = st.session_state.embedding_status
    if not status['is_complete'] and status['background_task_running']:
        progress_pct = status['processed_queries'] / max(1, status['total_queries'])
        st.progress(progress_pct, text=f"Processing embeddings: {status['processed_queries']}/{status['total_queries']} queries")
        st.caption(f"⚡ Background embedding in progress - you can still use the app while this completes")

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
                    return_tokens=True
                )
                
                # Track token usage
                if token_usage:
                    add_token_usage(token_usage)
                    
            except Exception as exc:  # catch Ollama or other errors
                st.error(f"❌ Ollama call failed: {exc}")
                st.stop()

        # -------- Answer
        st.subheader("📜 Answer")
        st.write(answer)
        
        # -------- Token Usage for this query
        if token_usage:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    label="🪙 Tokens Used",
                    value=f"{token_usage['total_tokens']:,}",
                    delta=f"In: {token_usage['prompt_tokens']:,} | Out: {token_usage['completion_tokens']:,}"
                )
            
            with col2:
                st.metric(
                    label="🏠 Local Phi3",
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
    st.subheader("📊 Queries from BigQuery")
    
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