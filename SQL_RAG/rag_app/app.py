#!/usr/bin/env python3
"""
SQL RAG Streamlit Application

A clean, modularized SQL RAG application with three main interfaces:
- 🔍 Query Search: Vector search with Gemini optimization
- 📚 Query Catalog: Browse and search through all queries with analytics
- 💬 Chat: ChatGPT-like conversation interface

Usage:
    streamlit run app.py

Features:
- Modular architecture with clean separation of concerns
- Google Gemini 2.5 Flash integration with 1M context window
- Smart schema injection and hybrid search capabilities
- Real-time token usage tracking and analytics
- Cached analytics for optimal performance
"""

import streamlit as st
import logging
import sys
from pathlib import Path

# Import modular components
from modular.config import PAGE_NAMES
from modular.session_manager import session_manager
from modular.navigation import navigation
from modular.page_modules import search_page, catalog_page, chat_page

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit page config
st.set_page_config(
    page_title="SQL RAG with Gemini", 
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)


def initialize_application():
    """Initialize the application and load required data"""
    try:
        # Initialize session manager (loads session state)
        session_manager.initialize_session_state()
        
        # Load CSV data if not already loaded
        if not session_manager.load_csv_data_if_needed():
            st.error("❌ Failed to load CSV data. Cannot proceed.")
            st.stop()
        
        # Load schema manager if available
        session_manager.load_schema_manager_if_needed()
        
        # Load schema agent if available
        session_manager.load_schema_agent_if_needed()
        
        logger.info("✅ Application initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Application initialization failed: {e}")
        st.error(f"❌ Application initialization failed: {e}")
        st.stop()


def render_main_header():
    """Render the main application header"""
    st.title("🔥 SQL RAG with Gemini")
    st.caption("Ask questions about your SQL queries using Google Gemini 2.5 Flash with 1M context window")


def route_to_page(page_key: str):
    """
    Route to the appropriate page based on selection
    
    Args:
        page_key: Page identifier ('search', 'catalog', or 'chat')
    """
    try:
        if page_key == 'search':
            search_page.render()
        elif page_key == 'catalog':
            catalog_page.render()
        elif page_key == 'chat':
            chat_page.render()
        else:
            st.error(f"❌ Unknown page: {page_key}")
            logger.error(f"Unknown page requested: {page_key}")
    
    except Exception as e:
        st.error(f"❌ Error rendering page '{page_key}': {e}")
        logger.error(f"Error rendering page '{page_key}': {e}", exc_info=True)


def main():
    """Main application entry point"""
    try:
        # Initialize application
        initialize_application()
        
        # Render main header
        render_main_header()
        
        # Get current page from session state or default to search
        current_page_name = st.session_state.get('page_selection', PAGE_NAMES['search'])
        current_page_key = navigation.get_page_from_selection(current_page_name)
        
        # Render sidebar and get any page-specific configuration
        selected_vector_index = navigation.render_sidebar(current_page_name)
        
        # Update session state if page changed
        if current_page_name != st.session_state.get('last_page_selection'):
            st.session_state.last_page_selection = current_page_name
            logger.info(f"Page changed to: {current_page_name}")
        
        # Store selected vector index in session state for pages that need it
        if selected_vector_index:
            if st.session_state.get('selected_vector_index') != selected_vector_index:
                st.session_state.selected_vector_index = selected_vector_index
                logger.info(f"Vector store selection changed to: {selected_vector_index}")
        
        # Route to the appropriate page
        route_to_page(current_page_key)
        
    except Exception as e:
        st.error(f"❌ Application error: {e}")
        logger.error(f"Application error: {e}", exc_info=True)
        
        # Show error details in expandable section
        with st.expander("🔍 Error Details", expanded=False):
            st.code(str(e))
            st.caption("Check the logs for more information.")


def show_startup_instructions():
    """Show startup instructions if data is not available"""
    st.warning("⚠️ Application setup required")
    
    st.markdown("""
    ### 📋 Setup Instructions
    
    To use this application, you need to prepare your data first:
    
    1. **Generate Vector Store:**
       ```bash
       python standalone_embedding_generator.py --csv "your_data.csv"
       ```
    
    2. **Generate Analytics Cache (Optional but recommended):**
       ```bash
       python catalog_analytics_generator.py --csv "your_data.csv"
       ```
    
    3. **Run the Application:**
       ```bash
       streamlit run app.py
       ```
    
    ### 📁 Required Files
    - CSV file with SQL queries (e.g., `sample_queries_with_metadata.csv`)
    - Vector store directory (`faiss_indices/`)
    - Analytics cache directory (`catalog_analytics/`) - optional
    - Schema file (`schema.csv`) - optional for smart schema injection
    """)


# Application entry point
if __name__ == "__main__":
    try:
        # Check if basic requirements are met
        from modular.data_loader import validate_data_files
        validation_status = validate_data_files()
        
        # Check critical requirements
        if not validation_status['vector_store']['exists'] or not validation_status['csv_data']['exists']:
            show_startup_instructions()
        else:
            main()
            
    except ImportError as e:
        st.error(f"❌ Import error: {e}")
        st.error("Make sure you're running this from the correct directory and all dependencies are installed.")
    except Exception as e:
        st.error(f"❌ Startup error: {e}")
        logger.error(f"Startup error: {e}", exc_info=True)