"""
Progressive Vector Store Builder Module

This extension to embeddings_generation.py adds support for progressive loading
with background embedding generation.
"""

import pathlib
import threading
import time
import hashlib
import pandas as pd
import os
import streamlit as st
from typing import List, Optional, Union, Dict
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from utils.embedding_provider import get_embedding_function

def _compute_document_hash(document: Document) -> str:
    """Generate a unique hash for a document."""
    content = document.page_content
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def build_progressive_vector_store(
    dataframe: pd.DataFrame,
    index_directory: pathlib.Path,
    initial_batch_size: int = 100,
    force_rebuild: bool = False,
    batch_size: int = 50,
    max_workers: int = 4
):
    """
    Two-phase vector store building:
    1. Process initial batch quickly for immediate use
    2. Process remaining documents in background
    
    Returns the initial vector store immediately.
    
    Args:
        dataframe: DataFrame containing queries
        index_directory: Directory to store FAISS index
        initial_batch_size: Number of documents to process immediately
        force_rebuild: If True, rebuild index regardless of change detection
        batch_size: Size of batches for parallel processing
        max_workers: Number of worker threads for parallel processing
        
    Returns:
        FAISS vector store ready for immediate use
    """
    from actions.embeddings_generation import _load_queries_from_dataframe, _create_embedding_batch
    
    # Initialize embedding model (Ollama or OpenAI)
    embeddings = get_embedding_function()
    
    # Create unique index path
    source_identifier = "bigquery_data"
    index_path = index_directory / f"index_{source_identifier}"
    
    # Ensure directory exists
    os.makedirs(index_path.parent, exist_ok=True)
    
    # Track total size
    total_size = len(dataframe)
    
    # Initialize embedding status in session state if it doesn't exist
    if 'embedding_status' not in st.session_state:
        st.session_state.embedding_status = {
            'total_queries': total_size,
            'processed_queries': 0,
            'is_complete': False,
            'background_task_running': False
        }
    else:
        st.session_state.embedding_status['total_queries'] = total_size
    
    # If vector store exists and we're not forcing rebuild, load it
    if not force_rebuild and index_path.exists() and index_path.is_dir():
        try:
            print(f"Loading existing vector store from {index_path}")
            vector_store = FAISS.load_local(
                str(index_path),
                embeddings,
                allow_dangerous_deserialization=True
            )
            
            # Mark as complete if this is a full rebuild
            if hasattr(vector_store, 'docstore') and hasattr(vector_store.docstore, '_dict'):
                processed_count = len(vector_store.docstore._dict)
                st.session_state.embedding_status['processed_queries'] = processed_count
                st.session_state.embedding_status['is_complete'] = (processed_count >= total_size)
                
            return vector_store
        except Exception as e:
            print(f"Error loading existing vector store: {e}")
    
    # Process the initial batch for immediate use
    initial_df = dataframe.head(initial_batch_size)
    initial_docs = _load_queries_from_dataframe(initial_df)
    
    # Create initial vector store
    print(f"🔧 Creating initial vector store with {len(initial_docs)} documents")
    vector_store = FAISS.from_documents(initial_docs, embeddings)
    
    # Save initial vector store
    vector_store.save_local(str(index_path))
    
    # Update status
    st.session_state.embedding_status['processed_queries'] = len(initial_docs)
    
    # Define background processing function
    def process_remaining_in_background():
        try:
            # Only process remaining if there are more
            if len(dataframe) > initial_batch_size:
                remaining_df = dataframe.iloc[initial_batch_size:]
                
                # Process remaining documents
                remaining_docs = _load_queries_from_dataframe(remaining_df)
                
                if remaining_docs:
                    print(f"🔧 Processing remaining {len(remaining_docs)} documents in background")
                    
                    # Create batches
                    batches = [remaining_docs[i:i + batch_size] for i in range(0, len(remaining_docs), batch_size)]
                    
                    # Process batches and update vector store
                    for batch_idx, batch in enumerate(batches):
                        try:
                            # Process batch 
                            processed_batch = _create_embedding_batch(batch)
                            
                            # Extract texts and metadatas for add_texts method
                            texts = [doc.page_content for doc in processed_batch]
                            metadatas = [doc.metadata for doc in processed_batch]
                            
                            # Add to vector store (requires loading the latest version)
                            current_store = FAISS.load_local(
                                str(index_path),
                                embeddings,
                                allow_dangerous_deserialization=True
                            )
                            current_store.add_texts(texts=texts, metadatas=metadatas)
                            current_store.save_local(str(index_path))
                            
                            # Update status
                            processed_so_far = initial_batch_size + (batch_idx + 1) * batch_size
                            processed_so_far = min(processed_so_far, total_size)
                            st.session_state.embedding_status['processed_queries'] = processed_so_far
                            
                            print(f"✅ Background processed batch {batch_idx+1}/{len(batches)}")
                            time.sleep(0.1)  # Small delay to prevent high CPU usage
                            
                        except Exception as batch_error:
                            print(f"Error processing batch {batch_idx+1}: {batch_error}")
                
                # Mark as complete
                st.session_state.embedding_status['is_complete'] = True
                print(f"✅ Background processing complete: all {total_size} documents embedded")
            else:
                # If there were no more to process, mark as complete
                st.session_state.embedding_status['is_complete'] = True
                print("✅ All documents already processed")
                
        except Exception as e:
            print(f"Background processing error: {e}")
        finally:
            # Mark background task as complete regardless
            st.session_state.embedding_status['background_task_running'] = False
    
    # Start background thread if not already running
    if not st.session_state.embedding_status['background_task_running'] and not st.session_state.embedding_status['is_complete']:
        st.session_state.embedding_status['background_task_running'] = True
        threading.Thread(target=process_remaining_in_background, daemon=True).start()
    
    return vector_store
