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
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# LangChain imports
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Import our simplified RAG function
from simple_rag_simple import answer_question_simple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
FAISS_INDICES_DIR = Path(__file__).parent / "faiss_indices"
DEFAULT_VECTOR_STORE = "index_queries_with_descriptions (1)"  # Expected index name

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
    
    # Sidebar for vector store selection
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Vector store selection
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
    
    # Load vector store
    if 'vector_store' not in st.session_state or st.session_state.get('current_index') != selected_index:
        with st.spinner(f"Loading vector store: {selected_index}..."):
            vector_store = load_vector_store(selected_index)
            
            if vector_store:
                st.session_state.vector_store = vector_store
                st.session_state.current_index = selected_index
                st.success(f"✅ Loaded {len(vector_store.docstore._dict):,} documents")
            else:
                st.stop()
    
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

if __name__ == "__main__":
    main()