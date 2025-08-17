#!/usr/bin/env python3
"""
Chat Page for Modular SQL RAG application.
Handles ChatGPT-like conversation interface with Gemini and Schema Agent support.
"""

import streamlit as st
import logging
from typing import Optional

from modular.config import PAGE_NAMES
from modular.session_manager import session_manager
from modular.vector_store_manager import vector_store_manager

# Add parent directory to path for imports
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Import chat system with schema agent support
try:
    from chat_system import create_chat_page
except ImportError as e:
    logging.error(f"Could not import chat_system: {e}")
    create_chat_page = None

# Configure logging
logger = logging.getLogger(__name__)


def render():
    """
    Render the chat page using the centralized chat_system module
    """
    try:
        # Ensure vector store is loaded
        if not vector_store_manager.load_vector_store_if_needed():
            st.error("❌ Cannot proceed without vector store. Please ensure the vector index is available.")
            st.info("💡 Use the Vector Store section in the sidebar to load an index.")
            return
        
        # Get required data from session state
        vector_store = session_manager.get_vector_store()
        csv_data = session_manager.get_csv_data()
        
        if not vector_store:
            st.error("❌ Vector store not available in session state")
            return
        
        if not csv_data:
            st.error("❌ CSV data not available in session state")
            return
        
        # Use the centralized chat system with schema agent support
        if create_chat_page:
            create_chat_page(vector_store, csv_data)
        else:
            st.error("❌ Chat system not available. Please check your installation.")
            
    except Exception as e:
        logger.error(f"Error in chat page: {e}", exc_info=True)
        st.error(f"❌ Error rendering chat page: {e}")
        
        # Show error details in expandable section for debugging
        with st.expander("🔍 Error Details", expanded=False):
            st.code(str(e))
            st.caption("Check the logs for more information.")


class ChatPage:
    """Chat page class for backward compatibility"""
    
    def __init__(self):
        self.page_title = PAGE_NAMES['chat']
    
    def render(self):
        """Render the chat page"""
        render()


# Create default instance for direct module usage
chat_page = ChatPage()

# Export the render function for direct usage
__all__ = ['render', 'ChatPage', 'chat_page']