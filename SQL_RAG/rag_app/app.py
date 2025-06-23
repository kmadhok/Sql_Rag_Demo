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
from groq import Groq
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

from simple_rag import answer_question, DATA_DIR, _build_or_load_vector_store, generate_description  # noqa: E402  (after sys.path tweak)

# Load environment variables from any .env up the tree
load_dotenv(find_dotenv(), override=False)

# --------------------------------------------------------------------------- #
#  Token tracking and cost calculation utilities
# --------------------------------------------------------------------------- #

# Model pricing (per 1M tokens)
MODEL_PRICING = {
    'llama3-70b-8192': {
        'input': 0.59,   # Groq pricing for Llama 70B
        'output': 0.79
    },
    'llama3-8b-8192': {
        'input': 0.05,   # Groq pricing for Llama 8B
        'output': 0.08
    },
    'gemini-1.5-flash': {
        'input_small': 0.075,    # <= 128k tokens
        'input_large': 0.15,     # > 128k tokens
        'output_small': 0.30,    # <= 128k tokens
        'output_large': 0.60     # > 128k tokens
    }
}

def calculate_cost(token_usage: dict, model_name: str = None) -> dict:
    """Calculate cost for token usage based on model pricing."""
    if not token_usage:
        return {'input_cost': 0, 'output_cost': 0, 'total_cost': 0}
    
    model = model_name or token_usage.get('model', 'llama3-70b-8192')
    prompt_tokens = token_usage.get('prompt_tokens', 0)
    completion_tokens = token_usage.get('completion_tokens', 0)
    
    if model in ['llama3-70b-8192', 'llama3-8b-8192']:
        pricing = MODEL_PRICING[model]
        input_cost = (prompt_tokens / 1_000_000) * pricing['input']
        output_cost = (completion_tokens / 1_000_000) * pricing['output']
    elif 'gemini' in model.lower():
        pricing = MODEL_PRICING['gemini-1.5-flash']
        # Use small pricing for simplicity (most queries will be <= 128k)
        input_cost = (prompt_tokens / 1_000_000) * pricing['input_small']
        output_cost = (completion_tokens / 1_000_000) * pricing['output_small']
    else:
        # Default to Llama 70B pricing
        pricing = MODEL_PRICING['llama3-70b-8192']
        input_cost = (prompt_tokens / 1_000_000) * pricing['input']
        output_cost = (completion_tokens / 1_000_000) * pricing['output']
    
    return {
        'input_cost': input_cost,
        'output_cost': output_cost,
        'total_cost': input_cost + output_cost
    }

def get_session_token_stats():
    """Get cumulative token statistics for the session."""
    if 'token_usage' not in st.session_state:
        st.session_state.token_usage = []
    
    total_prompt = sum(usage.get('prompt_tokens', 0) for usage in st.session_state.token_usage)
    total_completion = sum(usage.get('completion_tokens', 0) for usage in st.session_state.token_usage)
    total_tokens = total_prompt + total_completion
    
    # Calculate total costs for different models
    llama70b_cost = sum(calculate_cost(usage, 'llama3-70b-8192')['total_cost'] for usage in st.session_state.token_usage)
    gemini_cost = sum(calculate_cost(usage, 'gemini-1.5-flash')['total_cost'] for usage in st.session_state.token_usage)
    
    return {
        'total_tokens': total_tokens,
        'prompt_tokens': total_prompt,
        'completion_tokens': total_completion,
        'llama70b_cost': llama70b_cost,
        'gemini_cost': gemini_cost,
        'query_count': len(st.session_state.token_usage)
    }

def add_token_usage(token_usage: dict):
    """Add token usage to session state tracking."""
    if 'token_usage' not in st.session_state:
        st.session_state.token_usage = []
    st.session_state.token_usage.append(token_usage)

def display_session_usage():
    """Displays the session token usage and cost information."""
    stats = get_session_token_stats()
    if stats['query_count'] > 0:
        st.markdown("""
        <style>
            .usage-container {
                background-color: #262730; /* Streamlit dark theme background */
                color: white;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-around;
                align-items: center;
                flex-wrap: wrap;
            }
            .usage-container strong {
                color: white;
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
            .llama-cost { color: #90EE90; } /* light green */
            .gemini-cost { color: #87CEEB; } /* sky blue */
        </style>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="usage-container">
            <span class="usage-label">📊 Session Usage</span>
            <span class="usage-stat">🪙 Tokens: {stats['total_tokens']:,}</span>
            <span class="usage-stat">💬 Queries: {stats['query_count']}</span>
            <span class="usage-stat llama-cost">🦙 Llama 70B: ${stats['llama70b_cost']:.6f}</span>
            <span class="usage-stat gemini-cost">💎 Gemini Flash: ${stats['gemini_cost']:.6f}</span>
        </div>
        """, unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
#  Page config & small helpers
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Retail-SQL RAG", layout="wide")

# --------------------------------------------------------------------------- #
#  Top-level navigation (Chat vs. Catalog)
# --------------------------------------------------------------------------- #

PAGE = st.sidebar.radio("Navigation", ["🔎 Chat", "📚 Catalog"], key="nav")

# Shared header
st.title("🛍️  Retail SQL Knowledge Base")

# Token counter in top right corner is being moved below

DESC_PATH = APP_DIR / "query_descriptions.json"

def _load_desc_cache() -> dict[str, str]:
    if DESC_PATH.exists():
        try:
            return json.loads(DESC_PATH.read_text())
        except Exception:
            return {}
    return {}

_DESC_CACHE: dict[str, str] = _load_desc_cache()

def _save_desc_cache() -> None:
    try:
        DESC_PATH.write_text(json.dumps(_DESC_CACHE, indent=2))
    except Exception:
        pass

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
    
    # Show detailed pricing information
    with st.expander("💰 Model Pricing (per 1M tokens)"):
        st.markdown("""
        **Groq Models:**
        - 🦙 Llama 70B: $0.59 in / $0.79 out
        - 🦙 Llama 8B: $0.05 in / $0.08 out
        
        **Gemini 1.5 Flash:**
        - 💎 ≤128k tokens: $0.075 in / $0.30 out
        - 💎 >128k tokens: $0.15 in / $0.60 out
        
        *Current app uses Llama 70B for main queries and Llama 8B for descriptions.*
        """)
    
    # Show session statistics
    if 'token_usage' in st.session_state and st.session_state.token_usage:
        stats = get_session_token_stats()
        st.metric("Total Tokens", f"{stats['total_tokens']:,}")
        st.metric("Total Queries", stats['query_count'])
        
        st.markdown("**Estimated Costs:**")
        st.markdown(f"🦙 Llama 70B: ${stats['llama70b_cost']:.6f}")
        st.markdown(f"💎 Gemini Flash: ${stats['gemini_cost']:.6f}")

# --------------------------------------------------------------------------- #
#  Main interaction
# --------------------------------------------------------------------------- #
if PAGE == "🔎 Chat":
    query = st.text_input("Ask a question about the retail codebase:", placeholder="e.g. Which query joins inventory with sales?")

    display_session_usage()

    if st.button("🔍  Ask") and query.strip():
        with st.spinner("Thinking…"):
            try:
                answer, docs, token_usage = answer_question(query, k=k, return_docs=True, return_tokens=True)
                
                # Track token usage
                if token_usage:
                    add_token_usage(token_usage)
                    
            except Exception as exc:  # catch Groq or other errors
                st.error(f"❌ LLM call failed: {exc}")
                st.stop()

        # -------- Answer
        st.subheader("📜 Answer")
        st.write(answer)
        
        # -------- Token Usage for this query
        if token_usage:
            cost_info = calculate_cost(token_usage)
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="🪙 Tokens Used",
                    value=f"{token_usage['total_tokens']:,}",
                    delta=f"In: {token_usage['prompt_tokens']:,} | Out: {token_usage['completion_tokens']:,}"
                )
            
            with col2:
                st.metric(
                    label="🦙 Llama 70B Cost",
                    value=f"${cost_info['total_cost']:.6f}",
                    delta=f"In: ${cost_info['input_cost']:.6f} | Out: ${cost_info['output_cost']:.6f}"
                )
            
            with col3:
                gemini_cost = calculate_cost(token_usage, 'gemini-1.5-flash')
                st.metric(
                    label="💎 Gemini Flash Cost",
                    value=f"${gemini_cost['total_cost']:.6f}",
                    delta=f"In: ${gemini_cost['input_cost']:.6f} | Out: ${gemini_cost['output_cost']:.6f}"
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

                    # full file / query
                    try:
                        full_text = (DATA_DIR / path).read_text(encoding="utf-8")
                    except Exception as exc:
                        st.error(f"Could not read full file: {exc}")
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

    st.subheader("📚 Query Catalog")

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
    
    # Gather .sql files in project
    sql_files = sorted([p for p in DATA_DIR.rglob("*.sql")])

    for p in sql_files:
        joins = _scan_joins(p.read_text(encoding="utf-8"))
        for j in joins:
            row = {"File": str(p.relative_to(DATA_DIR))}
            row.update(j)
            join_rows.append(row)

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

        transform_rows = []
        for p in sql_files:
            for t in _scan_transforms(p.read_text(encoding="utf-8")):
                transform_rows.append(
                    {"Transformation": t, "File": str(p.relative_to(DATA_DIR))}
                )

        if transform_rows:
            st.subheader("🛠️ SQL Transformations")
            import pandas as pd
            df_trans = (
                pd.DataFrame(transform_rows)
                .sort_values(["Transformation", "File"])
                .reset_index(drop=True)
            )
            st.dataframe(df_trans, use_container_width=True, hide_index=True)

    st.divider()

    # ------------------------------------------------------
    # Full-text search over all SQL / Python chunks with FAISS
    # ------------------------------------------------------

    search_query = st.text_input("🔍 Full-text search across codebase", key="global_search")
    if search_query:
        vs = _build_or_load_vector_store()
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

    @st.cache_data(show_spinner="Generating descriptions …")
    def _describe(path_str: str) -> str:
        """Return cached description, generating & persisting if missing."""
        cached = _DESC_CACHE.get(path_str)
        if cached and not cached.startswith("Description unavailable"):
            return cached

        full_sql = (DATA_DIR / path_str).read_text(encoding="utf-8")
        
        try:
            desc, token_usage = generate_description(full_sql)
            
            # Track token usage for description generation
            if token_usage and token_usage.get('total_tokens', 0) > 0:
                add_token_usage(token_usage)
                
        except Exception as exc:
            desc = f"Description unavailable ({exc})"

        _DESC_CACHE[path_str] = desc
        _save_desc_cache()
        return desc

    for p in sql_files:
        rel = str(p.relative_to(DATA_DIR))
        with st.expander(rel):
            st.markdown(f"*{_describe(rel)}*")
            st.code(_format_snippet(p.read_text(encoding="utf-8"), rel), language="sql")