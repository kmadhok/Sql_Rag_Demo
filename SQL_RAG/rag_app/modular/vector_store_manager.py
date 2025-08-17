#!/usr/bin/env python3
"""
Vector store management functionality for Modular SQL RAG application.
"""

import streamlit as st
import logging
import json
from pathlib import Path
from typing import Optional, List

from modular.config import FAISS_INDICES_DIR, DEFAULT_VECTOR_STORE
from modular.utils import get_available_indices
from modular.data_loader import load_vector_store

# Configure logging
logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages vector store operations and caching"""
    
    def __init__(self):
        self.current_vector_store = None
        self.current_index_name = None
    
    def get_available_indices(self) -> List[str]:
        """Get list of available vector store indices"""
        return get_available_indices(FAISS_INDICES_DIR)
    
    def load_vector_store(self, index_name: str = DEFAULT_VECTOR_STORE, force_reload: bool = False):
        """
        Load vector store with caching
        
        Args:
            index_name: Name of the index to load
            force_reload: Force reload even if already loaded
            
        Returns:
            FAISS vector store or None if loading fails
        """
        # Return cached version if already loaded and not forcing reload
        if not force_reload and self.current_vector_store and self.current_index_name == index_name:
            return self.current_vector_store
        
        # Load the vector store
        vector_store = load_vector_store(index_name)
        
        if vector_store:
            self.current_vector_store = vector_store
            self.current_index_name = index_name
            logger.info(f"Vector store loaded: {index_name}")
        
        return vector_store
    
    def get_vector_store_info(self, index_name: str) -> dict:
        """
        Get information about a vector store
        
        Args:
            index_name: Name of the index
            
        Returns:
            Dictionary with vector store information
        """
        index_path = FAISS_INDICES_DIR / index_name
        info = {
            'name': index_name,
            'path': str(index_path),
            'exists': index_path.exists(),
            'documents': 0,
            'created_at': None,
            'gpu_accelerated': False
        }
        
        if not index_path.exists():
            return info
        
        # Try to get status information
        status_file = FAISS_INDICES_DIR / f"status_{index_name[6:]}.json"  # Remove "index_" prefix
        if status_file.exists():
            try:
                with open(status_file) as f:
                    status = json.load(f)
                
                info.update({
                    'documents': status.get('total_documents', 0),
                    'created_at': status.get('created_at', 'Unknown'),
                    'gpu_accelerated': status.get('gpu_acceleration', {}).get('gpu_accelerated_processing', False)
                })
            except Exception as e:
                logger.warning(f"Could not load status info for {index_name}: {e}")
        
        return info
    
    def display_vector_store_selection(self) -> Optional[str]:
        """
        Display vector store selection UI
        
        Returns:
            Selected index name or None if no indices available
        """
        available_indices = self.get_available_indices()
        
        if not available_indices:
            st.error("❌ No vector stores found!")
            st.info("💡 First run: python standalone_embedding_generator.py --csv 'your_data.csv'")
            return None
        
        # Let user select which vector store to use
        selected_index = st.selectbox(
            "📂 Select Vector Store:",
            available_indices,
            index=0 if DEFAULT_VECTOR_STORE not in available_indices else available_indices.index(DEFAULT_VECTOR_STORE)
        )
        
        return selected_index
    
    def display_vector_store_info(self, index_name: str):
        """
        Display vector store information in the sidebar
        
        Args:
            index_name: Name of the index to display info for
        """
        info = self.get_vector_store_info(index_name)
        
        if not info['exists']:
            st.error(f"Vector store {index_name} not found!")
            return
        
        st.subheader("📊 Vector Store Info")
        
        # Document count
        if info['documents']:
            st.metric("Total Documents", f"{info['documents']:,}")
        else:
            st.metric("Total Documents", "Unknown")
        
        # Creation date
        if info['created_at']:
            st.caption(f"Created: {info['created_at']}")
        
        # GPU acceleration
        if info['gpu_accelerated']:
            st.success("🚀 GPU-accelerated")
        else:
            st.info("💻 CPU processed")
    
    def ensure_vector_store_loaded(self, selected_index: str) -> bool:
        """
        Ensure vector store is loaded in session state
        
        Args:
            selected_index: Index name to load
            
        Returns:
            True if loaded successfully, False otherwise
        """
        # Check if we need to load or reload
        if ('vector_store' not in st.session_state or 
            st.session_state.get('current_index') != selected_index):
            
            with st.spinner(f"Loading vector store: {selected_index}..."):
                vector_store = self.load_vector_store(selected_index)
                
                if vector_store:
                    st.session_state.vector_store = vector_store
                    st.session_state.current_index = selected_index
                    
                    # Display success message
                    doc_count = len(vector_store.docstore._dict) if hasattr(vector_store, 'docstore') else 'Unknown'
                    st.success(f"✅ Loaded {doc_count:,} documents")
                    return True
                else:
                    st.error("Failed to load vector store")
                    return False
        
        return True


# Global instance for use throughout the application
vector_store_manager = VectorStoreManager()