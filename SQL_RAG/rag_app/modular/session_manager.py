#!/usr/bin/env python3
"""
Streamlit session state management for Modular SQL RAG application.
"""

import streamlit as st
import logging
from typing import Any, Dict, Optional
from pathlib import Path

from modular.data_loader import load_csv_data, load_schema_manager
from modular.config import SCHEMA_CSV_PATH

# Configure logging
logger = logging.getLogger(__name__)


class SessionManager:
    """Manages Streamlit session state and shared data"""
    
    def __init__(self):
        self._initialized = False
    
    def initialize_session_state(self):
        """Initialize all required session state variables"""
        if self._initialized:
            return
            
        # CSV data loading
        if 'csv_data' not in st.session_state:
            st.session_state.csv_data = None
        
        # Schema manager
        if 'schema_manager' not in st.session_state:
            st.session_state.schema_manager = None
        
        # Schema agent
        if 'schema_agent' not in st.session_state:
            st.session_state.schema_agent = None
        
        # Vector store
        if 'vector_store' not in st.session_state:
            st.session_state.vector_store = None
        
        if 'current_index' not in st.session_state:
            st.session_state.current_index = None
        
        # Token usage tracking
        if 'token_usage' not in st.session_state:
            st.session_state.token_usage = []
        
        # Chat messages
        if 'chat_messages' not in st.session_state:
            st.session_state.chat_messages = []
        
        # Page state
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'search'
            
        self._initialized = True
    
    def load_csv_data_if_needed(self) -> bool:
        """
        Load CSV data if not already loaded
        
        Returns:
            True if data is available, False otherwise
        """
        if st.session_state.csv_data is None:
            logger.info("Loading CSV data...")
            csv_data = load_csv_data()
            
            if csv_data is not None:
                st.session_state.csv_data = csv_data
                logger.info(f"CSV data loaded: {len(csv_data)} queries")
                return True
            else:
                st.error("Cannot proceed without CSV data")
                return False
        
        return True
    
    def load_schema_manager_if_needed(self):
        """Load schema manager if not already loaded"""
        if st.session_state.schema_manager is None:
            logger.info("Loading schema manager...")
            schema_manager = load_schema_manager()
            st.session_state.schema_manager = schema_manager
            
            if schema_manager:
                logger.info(f"✅ Schema manager ready: {schema_manager.table_count} tables available for injection")
            else:
                logger.info("Schema manager not available - proceeding without schema injection")
    
    def load_schema_agent_if_needed(self):
        """Load schema agent if not already loaded"""
        if st.session_state.schema_agent is None:
            logger.info("Loading schema agent...")
            try:
                # Import here to avoid circular imports
                import sys
                parent_dir = Path(__file__).parent.parent
                if str(parent_dir) not in sys.path:
                    sys.path.insert(0, str(parent_dir))
                
                from core.schema_agent import SchemaAgent
                
                # Initialize schema agent with the CSV path
                schema_agent = SchemaAgent(str(SCHEMA_CSV_PATH))
                st.session_state.schema_agent = schema_agent
                
                if schema_agent.is_available():
                    logger.info(f"✅ Schema agent ready: {schema_agent.get_table_count()} tables, {schema_agent.get_column_count()} columns")
                else:
                    logger.info("Schema agent loaded but no schema data available")
                    
            except Exception as e:
                logger.warning(f"Schema agent initialization failed: {e}")
                st.session_state.schema_agent = None
    
    def get_csv_data(self):
        """Get CSV data from session state"""
        return st.session_state.csv_data
    
    def get_schema_manager(self):
        """Get schema manager from session state"""
        return st.session_state.schema_manager
    
    def get_vector_store(self):
        """Get vector store from session state"""
        return st.session_state.vector_store
    
    def add_token_usage(self, usage_data: Dict[str, Any]):
        """Add token usage data to session state"""
        if 'token_usage' not in st.session_state:
            st.session_state.token_usage = []
        
        st.session_state.token_usage.append(usage_data)
    
    def get_total_token_usage(self) -> Dict[str, Any]:
        """Get aggregated token usage statistics"""
        if not st.session_state.token_usage:
            return {
                'total_tokens': 0,
                'total_queries': 0,
                'total_cost': 0.0
            }
        
        total_tokens = sum(usage.get('total_tokens', 0) for usage in st.session_state.token_usage)
        total_queries = len(st.session_state.token_usage)
        
        return {
            'total_tokens': total_tokens,
            'total_queries': total_queries,
            'average_tokens_per_query': total_tokens / total_queries if total_queries > 0 else 0
        }
    
    def add_chat_message(self, role: str, content: str, **kwargs):
        """Add a message to the chat history"""
        message = {
            'role': role,
            'content': content,
            **kwargs
        }
        st.session_state.chat_messages.append(message)
    
    def get_chat_messages(self):
        """Get chat messages from session state"""
        return st.session_state.chat_messages
    
    def clear_chat_messages(self):
        """Clear all chat messages"""
        st.session_state.chat_messages = []
        # Also clear token usage if desired
        st.session_state.token_usage = []
    
    def set_current_page(self, page_name: str):
        """Set the current page"""
        st.session_state.current_page = page_name
    
    def get_current_page(self) -> str:
        """Get the current page"""
        return st.session_state.current_page
    
    def display_session_stats(self):
        """Display session statistics in the sidebar or main area"""
        if not st.session_state.token_usage:
            return
        
        stats = self.get_total_token_usage()
        
        if stats['total_queries'] > 0:
            st.markdown(f"""
            <div style="background-color: #262730; color: white; padding: 15px; border-radius: 10px; margin: 10px 0;">
                <strong>📊 Session Stats:</strong> 
                {stats['total_tokens']:,} tokens | {stats['total_queries']} queries | 🔥 Gemini-Optimized | 🤖 Google Gemini 2.5 Flash
            </div>
            """, unsafe_allow_html=True)
    
    def reset_session(self):
        """Reset all session state variables"""
        # Keep CSV data and schema manager as they're expensive to reload
        keys_to_keep = ['csv_data', 'schema_manager']
        
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
        
        # Reinitialize
        self.initialize_session_state()
        logger.info("Session state reset")
    
    def get_conversation_context(self, exclude_last: bool = True) -> str:
        """
        Get conversation context from chat messages
        
        Args:
            exclude_last: Whether to exclude the last message (useful when generating response)
            
        Returns:
            Formatted conversation context string
        """
        messages = st.session_state.chat_messages
        if exclude_last and len(messages) > 0:
            messages = messages[:-1]
        
        conversation_context = ""
        for msg in messages:
            if msg['role'] == 'user':
                conversation_context += f"User: {msg['content']}\n"
            else:
                conversation_context += f"Assistant: {msg['content']}\n"
        
        return conversation_context


# Global instance for use throughout the application
session_manager = SessionManager()