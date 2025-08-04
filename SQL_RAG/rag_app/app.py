"""
Retail-SQL RAG – Streamlit front-end
Run with:
    streamlit run rag_app/app.py
"""

from __future__ import annotations

import pathlib
import sys
from typing import List, Dict

import sqlparse
import streamlit as st
from functools import lru_cache
import json
import re
import os

from collections import defaultdict
import graphviz
from rapidfuzz import fuzz
from dotenv import load_dotenv, find_dotenv

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

from simple_rag import answer_question, _build_or_load_vector_store  # noqa: E402  (after sys.path tweak)

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

# Hardcoded CSV path - no user selection needed
SAMPLE_QUERIES_CSV = pathlib.Path(__file__).resolve().parent.parent / "sample_queries.csv"

# Shared header
st.title("🛍️  Retail SQL Knowledge Base")
st.caption(f"📄 {SAMPLE_QUERIES_CSV.name} • Auto-generated descriptions • Local Phi3 model")

# --- Manage and cache the vector store in session state ---
if 'vector_store' not in st.session_state:
    try:
        # Check if sample_queries.csv exists
        if not SAMPLE_QUERIES_CSV.exists():
            st.error(f"❌ Required file not found: {SAMPLE_QUERIES_CSV}")
            st.error("Please ensure sample_queries.csv exists in the project root directory.")
            st.stop()
        
        # Always rebuild vector embeddings (fast) and generate missing descriptions (slow)
        with st.spinner(f"🔄 Processing queries from {SAMPLE_QUERIES_CSV.name}..."):
            st.session_state.vector_store = _build_or_load_vector_store(csv_path=SAMPLE_QUERIES_CSV, force_rebuild=True)
        
        # Count total queries for confirmation
        import pandas as pd
        try:
            df = pd.read_csv(SAMPLE_QUERIES_CSV)
            query_count = len(df)
            st.success(f"✅ Knowledge base ready! Processed {query_count} queries from {SAMPLE_QUERIES_CSV.name}")
            st.info(f"📊 Vector embeddings and descriptions generated for all {query_count} queries")
        except Exception:
            st.success(f"✅ Knowledge base ready! Processed {SAMPLE_QUERIES_CSV.name}")
        
    except Exception as e:
        st.error(f"Failed to load knowledge base: {e}")
        st.stop()
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
    
    # CSV mode - analyze joins from queries in sample_queries.csv
    try:
        import pandas as pd
        df = pd.read_csv(SAMPLE_QUERIES_CSV)
        
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
        st.error(f"Error analyzing joins from CSV: {e}")
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

    # Show queries from hardcoded CSV  
    st.subheader(f"📊 Queries from {SAMPLE_QUERIES_CSV.name}")
    
    try:
        # Read CSV and display queries
        import pandas as pd
        df = pd.read_csv(SAMPLE_QUERIES_CSV)
        
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