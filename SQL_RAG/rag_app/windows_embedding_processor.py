#!/usr/bin/env python3
"""
Windows Embedding Processor - Auto-Detection Mode

A Windows-compatible replacement for SmartEmbeddingProcessor that uses
process-based parallelism instead of threading to avoid Streamlit freezing issues.

This module automatically detects Windows and provides seamless compatibility
while maintaining the same interface as the original processor.
"""

import os
import time
import platform
import logging
import hashlib
import multiprocessing
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

# Configure logging
logger = logging.getLogger(__name__)


def process_document_batch_worker(batch_data: Tuple[List[Document], str]) -> Optional[FAISS]:
    """
    Worker function for processing a batch of documents in a separate process
    This function is designed to be Windows-compatible with multiprocessing
    
    Args:
        batch_data: Tuple of (documents_batch, embedding_model_name)
        
    Returns:
        FAISS vector store or None if failed
    """
    documents_batch, model_name = batch_data
    
    try:
        # Initialize embeddings in this process
        embeddings = OllamaEmbeddings(model=model_name)
        
        # Create vector store from batch
        vector_store = FAISS.from_documents(documents_batch, embeddings)
        return vector_store
        
    except Exception as e:
        logger.error(f"Error processing batch in worker: {e}")
        return None


class WindowsEmbeddingProcessor:
    """
    Windows-compatible embedding processor using multiprocessing instead of threading
    
    Provides the same interface as SmartEmbeddingProcessor but uses Windows-safe
    processing methods to avoid Streamlit freezing issues.
    """
    
    def __init__(self, initial_batch_size: int = 100, chunk_size: int = 1000,
                 chunk_overlap: int = 150, max_workers: Optional[int] = None):
        """
        Initialize Windows-compatible embedding processor
        
        Args:
            initial_batch_size: Number of documents to process in first batch
            chunk_size: Text splitter chunk size
            chunk_overlap: Text splitter overlap
            max_workers: Number of processes (None = CPU count)
        """
        self.initial_batch_size = initial_batch_size
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_workers = max_workers or max(2, multiprocessing.cpu_count() - 1)
        
        # Initialize components
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        
        # State tracking
        self.current_data_hash = None
        self.index_dir = Path("faiss_indices")
        self.index_dir.mkdir(exist_ok=True)
        
        logger.info(f"🖥️ Windows-compatible processor initialized with {self.max_workers} workers")
    
    def _calculate_data_hash(self, df: pd.DataFrame, source_info: str) -> str:
        """Calculate hash for data change detection"""
        try:
            # Combine DataFrame content and source info
            df_str = df.to_string()
            combined = f"{df_str}:{source_info}"
            return hashlib.md5(combined.encode()).hexdigest()
        except Exception as e:
            logger.warning(f"Could not calculate data hash: {e}")
            return str(time.time())  # Fallback to timestamp
    
    def _create_documents(self, df: pd.DataFrame) -> List[Document]:
        """Create LangChain documents from DataFrame with composite content"""
        documents = []
        
        for idx, row in df.iterrows():
            # Create composite content for richer search
            content_parts = [f"Query: {row['query']}"]
            
            if 'description' in row and pd.notna(row['description']) and str(row['description']).strip():
                content_parts.append(f"Description: {row['description']}")
            
            if 'table' in row and pd.notna(row['table']) and str(row['table']).strip():
                content_parts.append(f"Tables: {row['table']}")
            
            if 'joins' in row and pd.notna(row['joins']) and str(row['joins']).strip():
                content_parts.append(f"Joins: {row['joins']}")
            
            content = "\n".join(content_parts)
            
            # Create document with metadata
            doc = Document(
                page_content=content,
                metadata={
                    'index': idx,
                    'query': row['query'],
                    'description': str(row.get('description', '')),
                    'table': str(row.get('table', '')),
                    'joins': str(row.get('joins', '')),
                    'source': 'data_source'
                }
            )
            documents.append(doc)
        
        return documents
    
    def _split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks"""
        return self.text_splitter.split_documents(documents)
    
    def _get_index_path(self, source_name: str) -> Path:
        """Get index path for a data source"""
        return self.index_dir / f"index_{source_name}"
    
    def _load_existing_index(self, index_path: Path) -> Optional[FAISS]:
        """Load existing FAISS index if available"""
        if not index_path.exists():
            return None
        
        try:
            vector_store = FAISS.load_local(
                str(index_path), 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info(f"✅ Loaded existing index with {len(vector_store.docstore._dict)} documents")
            return vector_store
        except Exception as e:
            logger.warning(f"Could not load existing index: {e}")
            return None
    
    def _save_index(self, vector_store: FAISS, index_path: Path, data_hash: str):
        """Save FAISS index and metadata"""
        try:
            vector_store.save_local(str(index_path))
            
            # Save metadata
            metadata = {
                'data_hash': data_hash,
                'created_at': time.time(),
                'document_count': len(vector_store.docstore._dict),
                'processor_type': 'windows_compatible'
            }
            
            import json
            metadata_path = index_path.parent / f"{index_path.name}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            logger.info(f"✅ Saved index with {metadata['document_count']} documents")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    def _check_data_changes(self, data_hash: str, index_path: Path) -> bool:
        """Check if data has changed since last processing"""
        metadata_path = index_path.parent / f"{index_path.name}_metadata.json"
        
        if not metadata_path.exists():
            return True  # No metadata, assume changes
        
        try:
            import json
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            return metadata.get('data_hash') != data_hash
        except Exception as e:
            logger.warning(f"Could not read metadata: {e}")
            return True
    
    def _process_initial_batch_sequential(self, documents: List[Document]) -> FAISS:
        """Process initial batch sequentially for reliability"""
        logger.info(f"🔧 Processing initial batch of {len(documents)} documents sequentially...")
        start_time = time.time()
        
        try:
            vector_store = FAISS.from_documents(documents, self.embeddings)
            processing_time = time.time() - start_time
            logger.info(f"✅ Initial batch processed in {processing_time:.1f}s")
            return vector_store
        except Exception as e:
            logger.error(f"Error processing initial batch: {e}")
            raise
    
    def _process_remaining_batches_parallel(self, documents: List[Document], 
                                          existing_store: FAISS, batch_size: int = 25) -> FAISS:
        """Process remaining documents in parallel batches"""
        if not documents:
            return existing_store
        
        logger.info(f"⚡ Processing {len(documents)} remaining documents in parallel...")
        logger.info(f"📊 Using {self.max_workers} processes with batch size {batch_size}")
        
        # Split into batches
        batches = [documents[i:i + batch_size] for i in range(0, len(documents), batch_size)]
        
        if not batches:
            return existing_store
        
        start_time = time.time()
        processed_stores = []
        
        # Prepare batch data for workers
        batch_data_list = [(batch, "nomic-embed-text") for batch in batches]
        
        try:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all batches
                future_to_batch = {
                    executor.submit(process_document_batch_worker, batch_data): i 
                    for i, batch_data in enumerate(batch_data_list)
                }
                
                # Collect results
                for future in as_completed(future_to_batch):
                    batch_idx = future_to_batch[future]
                    try:
                        vector_store = future.result()
                        if vector_store:
                            processed_stores.append(vector_store)
                            logger.info(f"✅ Completed batch {batch_idx + 1}/{len(batches)}")
                        else:
                            logger.warning(f"❌ Failed to process batch {batch_idx + 1}")
                    except Exception as e:
                        logger.error(f"Error in batch {batch_idx + 1}: {e}")
            
            # Merge all stores into existing store
            for store in processed_stores:
                existing_store.merge_from(store)
            
            processing_time = time.time() - start_time
            logger.info(f"⚡ Background processing completed in {processing_time:.1f}s")
            logger.info(f"📊 Total documents: {len(existing_store.docstore._dict)}")
            
            return existing_store
            
        except Exception as e:
            logger.error(f"Error in parallel processing: {e}")
            # Return existing store even if parallel processing fails
            return existing_store
    
    def process_embeddings(self, df: pd.DataFrame, source_name: str, 
                          source_info: str, progress_callback=None) -> FAISS:
        """
        Main method to process embeddings with Windows compatibility
        
        Args:
            df: DataFrame containing queries and metadata
            source_name: Name identifier for the data source
            source_info: Source information for change tracking
            progress_callback: Optional callback for progress updates
            
        Returns:
            FAISS vector store
        """
        logger.info(f"🖥️ Windows-compatible processing starting for {len(df)} documents")
        
        # Calculate data hash for change detection
        data_hash = self._calculate_data_hash(df, source_info)
        index_path = self._get_index_path(source_name)
        
        # Check for existing index and changes
        if not self._check_data_changes(data_hash, index_path):
            logger.info("📁 No data changes detected, loading existing index...")
            existing_store = self._load_existing_index(index_path)
            if existing_store:
                return existing_store
        
        if progress_callback:
            progress_callback("🔄 Creating documents...")
        
        # Create and split documents
        documents = self._create_documents(df)
        split_documents = self._split_documents(documents)
        
        logger.info(f"📄 Created {len(split_documents)} document chunks from {len(documents)} queries")
        
        if progress_callback:
            progress_callback(f"✅ Processing first {self.initial_batch_size} documents...")
        
        # Process initial batch
        initial_batch = split_documents[:self.initial_batch_size]
        vector_store = self._process_initial_batch_sequential(initial_batch)
        
        if progress_callback:
            progress_callback(f"✅ Processed {len(initial_batch)} documents")
        
        # Process remaining documents in background
        remaining_documents = split_documents[self.initial_batch_size:]
        
        if remaining_documents:
            if progress_callback:
                progress_callback(f"⚡ Background processing: {len(remaining_documents)} remaining...")
            
            vector_store = self._process_remaining_batches_parallel(
                remaining_documents, vector_store
            )
        
        # Save the complete index
        self._save_index(vector_store, index_path, data_hash)
        
        if progress_callback:
            progress_callback("✅ Windows-compatible processing completed!")
        
        logger.info("🎉 Windows-compatible embedding processing completed successfully")
        return vector_store


class CrossPlatformEmbeddingProcessor:
    """
    Cross-platform embedding processor that automatically selects the appropriate
    processing method based on the operating system
    """
    
    def __init__(self, **kwargs):
        """Initialize with automatic platform detection"""
        self.is_windows = platform.system() == 'Windows'
        
        if self.is_windows:
            logger.info("🖥️ Windows detected - using Windows-compatible processor")
            self.processor = WindowsEmbeddingProcessor(**kwargs)
        else:
            # Use original SmartEmbeddingProcessor for non-Windows systems
            try:
                from smart_embedding_processor import SmartEmbeddingProcessor
                logger.info("🐧 Non-Windows system - using standard processor")
                self.processor = SmartEmbeddingProcessor(**kwargs)
            except ImportError:
                logger.warning("SmartEmbeddingProcessor not available, using Windows processor")
                self.processor = WindowsEmbeddingProcessor(**kwargs)
    
    def process_embeddings(self, df: pd.DataFrame, source_name: str, 
                          source_info: str, progress_callback=None) -> FAISS:
        """Process embeddings using the appropriate processor"""
        if self.is_windows and progress_callback:
            progress_callback("🖥️ Windows-compatible processing enabled")
        
        return self.processor.process_embeddings(
            df, source_name, source_info, progress_callback
        )


def get_embedding_processor(**kwargs) -> CrossPlatformEmbeddingProcessor:
    """
    Factory function to get the appropriate embedding processor for the current platform
    
    Returns:
        CrossPlatformEmbeddingProcessor instance
    """
    return CrossPlatformEmbeddingProcessor(**kwargs)


# For backward compatibility
def create_windows_safe_processor(**kwargs) -> WindowsEmbeddingProcessor:
    """Create a Windows-safe embedding processor"""
    return WindowsEmbeddingProcessor(**kwargs)


if __name__ == "__main__":
    # Test the Windows processor
    import pandas as pd
    
    # Create test data
    test_data = pd.DataFrame({
        'query': [
            'SELECT * FROM customers',
            'SELECT COUNT(*) FROM orders',
            'SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id'
        ],
        'description': [
            'Get all customers',
            'Count total orders',
            'Customer order details with join'
        ],
        'table': ['customers', 'orders', 'customers,orders'],
        'joins': ['', '', 'c.id = o.customer_id']
    })
    
    # Test processor
    processor = get_embedding_processor()
    
    def test_callback(message):
        print(f"Progress: {message}")
    
    try:
        vector_store = processor.process_embeddings(
            test_data, 
            "test_data", 
            "test_source_info",
            progress_callback=test_callback
        )
        print(f"✅ Test completed successfully with {len(vector_store.docstore._dict)} documents")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()