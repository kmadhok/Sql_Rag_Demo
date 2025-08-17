#!/usr/bin/env python3
"""
Navigation and sidebar management for Modular SQL RAG application.
Handles page routing and configuration display.
"""

import streamlit as st
import logging
from typing import Optional

from modular.config import PAGE_NAMES, DEFAULT_VECTOR_STORE
from modular.session_manager import session_manager
from modular.vector_store_manager import vector_store_manager
from modular.data_loader import validate_data_files, get_data_loading_recommendations

# Configure logging
logger = logging.getLogger(__name__)


class Navigation:
    """Handles navigation and sidebar configuration"""
    
    def __init__(self):
        self.page_options = list(PAGE_NAMES.values())
    
    def render_page_selection(self) -> str:
        """Render page selection radio buttons"""
        st.header("📱 Navigation")
        
        page = st.radio(
            "Select Page:",
            self.page_options,
            key="page_selection"
        )
        
        return page
    
    def render_data_status(self):
        """Render data validation status and recommendations"""
        st.header("📊 Data Status")
        
        # Validate data files
        validation_status = validate_data_files()
        recommendations = get_data_loading_recommendations(validation_status)
        
        # Show quick status indicators
        col1, col2 = st.columns(2)
        
        with col1:
            if validation_status['vector_store']['exists']:
                st.success("✅ Vector Store")
            else:
                st.error("❌ Vector Store")
        
        with col2:
            if validation_status['csv_data']['exists']:
                st.success("✅ CSV Data")
            else:
                st.error("❌ CSV Data")
        
        # Show recommendations in expandable section
        with st.expander("📋 Setup Recommendations", expanded=False):
            for rec in recommendations:
                if rec.startswith("🔴"):
                    st.error(rec)
                elif rec.startswith("🟡"):
                    st.warning(rec)
                else:
                    st.success(rec)
    
    def render_vector_store_info(self, current_page: str):
        """Render vector store configuration for applicable pages"""
        if current_page in [PAGE_NAMES['search'], PAGE_NAMES['chat']]:
            st.header("⚙️ Vector Store")
            
            # Vector store selection
            available_indices = vector_store_manager.get_available_indices()
            
            if not available_indices:
                st.error("❌ No vector stores found!")
                st.info("💡 First run: python standalone_embedding_generator.py --csv 'your_data.csv'")
                return None
            
            if current_page == PAGE_NAMES['search']:
                # For search page, allow selection
                selected_index = st.selectbox(
                    "📂 Select Vector Store:",
                    available_indices,
                    index=0 if DEFAULT_VECTOR_STORE not in available_indices else available_indices.index(DEFAULT_VECTOR_STORE),
                    help="Choose which vector store to search"
                )
            else:
                # For chat page, use default
                selected_index = available_indices[0] if DEFAULT_VECTOR_STORE not in available_indices else DEFAULT_VECTOR_STORE
                st.info(f"📂 Using: {selected_index}")
            
            # Display vector store info
            vector_store_manager.display_vector_store_info(selected_index)
            
            return selected_index
        
        elif current_page == PAGE_NAMES['catalog']:
            st.header("📊 Catalog Info")
            
            # Show CSV data info for catalog
            csv_data = session_manager.get_csv_data()
            if csv_data is not None:
                st.metric("Total Queries", len(csv_data))
                st.caption("Browse and search through all queries")
            else:
                st.error("❌ No CSV data loaded")
            
            return None
        
        return None
    
    def render_session_info(self):
        """Render session information and statistics"""
        st.header("🔥 Session Info")
        
        # Display session stats if available
        session_manager.display_session_stats()
        
        # Show current session state info
        with st.expander("🔧 Session Details", expanded=False):
            # CSV data status
            csv_data = session_manager.get_csv_data()
            if csv_data is not None:
                st.success(f"✅ CSV Data: {len(csv_data)} queries loaded")
            else:
                st.error("❌ CSV Data: Not loaded")
            
            # Schema manager status  
            schema_manager = session_manager.get_schema_manager()
            if schema_manager:
                st.success(f"✅ Schema Manager: {schema_manager.table_count} tables")
            else:
                st.info("ℹ️ Schema Manager: Not available")
            
            # Vector store status
            vector_store = session_manager.get_vector_store()
            current_index = st.session_state.get('current_index')
            if vector_store and current_index:
                doc_count = len(vector_store.docstore._dict) if hasattr(vector_store, 'docstore') else 'Unknown'
                st.success(f"✅ Vector Store: {current_index} ({doc_count:,} docs)")
            else:
                st.info("ℹ️ Vector Store: Not loaded")
            
            # Token usage stats
            total_stats = session_manager.get_total_token_usage()
            if total_stats['total_queries'] > 0:
                st.info(f"📊 Token Usage: {total_stats['total_tokens']:,} tokens across {total_stats['total_queries']} queries")
            else:
                st.info("📊 Token Usage: No queries processed yet")
    
    def render_about_info(self):
        """Render about information"""
        st.header("ℹ️ About")
        
        st.markdown("""
        **Modular SQL RAG Application**
        
        A Streamlit application for querying SQL databases using natural language with RAG (Retrieval-Augmented Generation).
        
        **Features:**
        - 🔍 **Vector Search**: Find relevant SQL examples using semantic search
        - 📚 **Query Catalog**: Browse and search through all SQL queries
        - 💬 **Chat Interface**: ChatGPT-like conversation about SQL
        - 🔥 **Gemini-Optimized**: Uses Google Gemini 2.5 Flash with 1M context window
        - 🗃️ **Smart Schema Injection**: Automatically includes relevant database schema
        - 🔀 **Hybrid Search**: Combines vector and keyword search methods
        - 🎯 **Agent Specialization**: Use @explain, @create, @longanswer for specialized responses
        """)
        
        with st.expander("🛠️ Technical Details", expanded=False):
            st.markdown("""
            **Architecture:**
            - **Vector Store**: FAISS with OpenAI embeddings (via Ollama)
            - **LLM**: Google Gemini 2.5 Flash via Vertex AI
            - **Embeddings**: Ollama nomic-embed-text (local)
            - **Framework**: Streamlit with modular page architecture
            - **Schema Management**: Dynamic schema injection based on query context
            
            **Performance Optimizations:**
            - Cached analytics for catalog page
            - Pagination for large datasets
            - Smart deduplication and context prioritization
            - Background processing for large vector stores
            """)
    
    def render_reset_session_button(self):
        """Render reset session button"""
        st.header("🔄 Reset")
        
        if st.button("🔄 Reset Session", use_container_width=True, help="Clear all session data except cached files"):
            session_manager.reset_session()
            st.success("✅ Session reset successfully!")
            st.rerun()
    
    def render_sidebar(self, current_page: str) -> Optional[str]:
        """
        Render the complete sidebar with navigation and configuration
        
        Args:
            current_page: Currently selected page
            
        Returns:
            Selected vector store index if applicable, None otherwise
        """
        with st.sidebar:
            # Page selection
            selected_page = self.render_page_selection()
            
            st.divider()
            
            # Data status
            self.render_data_status()
            
            st.divider()
            
            # Vector store info (page-specific)
            selected_index = self.render_vector_store_info(current_page)
            
            st.divider()
            
            # Session info
            self.render_session_info()
            
            st.divider()
            
            # About info
            self.render_about_info()
            
            st.divider()
            
            # Reset session
            self.render_reset_session_button()
            
            return selected_index
    
    def get_page_from_selection(self, page_selection: str) -> str:
        """Get the internal page key from user selection"""
        for key, value in PAGE_NAMES.items():
            if value == page_selection:
                return key
        return 'search'  # Default fallback


# Global instance
navigation = Navigation()