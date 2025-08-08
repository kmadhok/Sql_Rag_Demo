#!/usr/bin/env python3
"""
Smart Embedding Processor - Clean, efficient embedding generation with incremental updates

Features:
- Direct OllamaEmbeddings integration
- ThreadPoolExecutor for parallel processing
- Incremental updates with change detection
- Composite embeddings for multiple fields
- Data source abstraction (CSV/BigQuery)
- FAISS IndexFlatL2 for exact results
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain.schema.document import Document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class SmartEmbeddingProcessor:
    """Smart embedding processor with incremental updates and parallel processing"""
    
    def __init__(self, vector_store_path: Union[str, Path], 
                 status_file_path: Union[str, Path],
                 embedding_model: str = "nomic-embed-text"):
        """
        Initialize the smart embedding processor
        
        Args:
            vector_store_path: Path to store FAISS index files
            status_file_path: Path to store processing status
            embedding_model: Ollama embedding model name
        """
        self.vector_store_path = Path(vector_store_path)
        self.status_file_path = Path(status_file_path)
        self.embedding_model = embedding_model
        
        # Initialize Ollama embeddings
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        logger.info(f"Initialized SmartEmbeddingProcessor with {embedding_model}")
        
        # Load or create status
        self.status = self._load_status()
    
    def _load_status(self) -> Dict[str, Any]:
        """Load processing status from file or create new"""
        if self.status_file_path.exists():
            try:
                with open(self.status_file_path, 'r') as f:
                    status = json.load(f)
                logger.info(f"Loaded existing status: {len(status.get('processed_sources', []))} sources tracked")
                return status
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not load status file: {e}, creating new")
        
        return {
            "processed_sources": [],  # List of processed data sources with hashes
            "last_updated": datetime.now().isoformat(),
            "total_processed": 0,
            "vector_store_exists": False
        }
    
    def _save_status(self):
        """Save current status to file"""
        self.status["last_updated"] = datetime.now().isoformat()
        
        try:
            self.status_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.status_file_path, 'w') as f:
                json.dump(self.status, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save status: {e}")
    
    def _calculate_data_hash(self, df: pd.DataFrame, source_info: str = "") -> str:
        """Calculate hash of DataFrame for change detection"""
        # Create a hash based on data content and source info
        data_str = f"{source_info}|{df.shape}|{df.columns.tolist()}"
        if not df.empty:
            # Sample first few rows for hash (efficient for large datasets)
            sample_data = df.head(min(100, len(df))).to_string()
            data_str += f"|{sample_data}"
        
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _create_composite_embedding_text(self, row: pd.Series) -> str:
        """Create composite text from multiple fields for embedding"""
        components = []
        
        # Core query field (required)
        if 'query' in row and pd.notna(row['query']):
            components.append(f"SQL QUERY: {row['query']}")
        
        # Optional description field
        if 'description' in row and pd.notna(row['description']) and row['description']:
            components.append(f"DESCRIPTION: {row['description']}")
        
        # Optional table field
        if 'table' in row and pd.notna(row['table']) and row['table']:
            components.append(f"TABLES: {row['table']}")
        
        # Optional joins field  
        if 'joins' in row and pd.notna(row['joins']) and row['joins']:
            components.append(f"JOINS: {row['joins']}")
        
        return "\n\n".join(components)
    
    def _create_documents_from_dataframe(self, df: pd.DataFrame, 
                                        source_name: str = "unknown") -> List[Document]:
        """Convert DataFrame to LangChain documents with composite embeddings"""
        documents = []
        
        for idx, (_, row) in enumerate(df.iterrows()):
            # Create composite embedding text
            page_content = self._create_composite_embedding_text(row)
            
            if not page_content.strip():
                logger.warning(f"Empty content for row {idx}, skipping")
                continue
            
            # Create metadata
            metadata = {
                "source": source_name,
                "row_index": idx,
                "chunk": idx  # For compatibility with existing code
            }
            
            # Add all available fields to metadata
            for col in df.columns:
                if pd.notna(row[col]) and row[col]:
                    metadata[col] = str(row[col])
            
            document = Document(
                page_content=page_content,
                metadata=metadata
            )
            documents.append(document)
        
        logger.info(f"Created {len(documents)} documents from {len(df)} rows")
        return documents
    
    def _process_batch_embeddings(self, documents: List[Document], 
                                 batch_size: int = 15) -> FAISS:
        """Process documents in batches to avoid Ollama timeouts"""
        if not documents:
            raise ValueError("No documents to process")
        
        logger.info(f"Processing {len(documents)} documents in batches of {batch_size}")
        
        # Create initial vector store with first batch
        first_batch = documents[:batch_size]
        logger.info(f"Creating initial vector store with {len(first_batch)} documents")
        
        start_time = time.time()
        vector_store = FAISS.from_documents(first_batch, self.embeddings)
        batch_time = time.time() - start_time
        logger.info(f"Initial batch processed in {batch_time:.1f}s")
        
        # Process remaining documents in batches
        remaining_docs = documents[batch_size:]
        if remaining_docs:
            logger.info(f"Processing {len(remaining_docs)} remaining documents in batches")
            
            for i in range(0, len(remaining_docs), batch_size):
                batch = remaining_docs[i:i + batch_size]
                batch_num = (i // batch_size) + 2
                
                logger.info(f"Processing batch {batch_num}: {len(batch)} documents")
                
                start_batch = time.time()
                # Extract texts and metadata for batch addition
                texts = [doc.page_content for doc in batch]
                metadatas = [doc.metadata for doc in batch]
                
                # Add to existing vector store
                vector_store.add_texts(texts=texts, metadatas=metadatas)
                
                batch_time = time.time() - start_batch
                logger.info(f"Batch {batch_num} processed in {batch_time:.1f}s")
                
                # Brief pause to avoid overwhelming Ollama
                time.sleep(0.1)
        
        return vector_store
    
    def _process_batch_parallel(self, documents: List[Document], 
                               max_workers: int = 3) -> List[Document]:
        """Process document batches in parallel using ThreadPoolExecutor"""
        if len(documents) <= 50:  # Small dataset, process sequentially
            return documents
        
        logger.info(f"Processing {len(documents)} documents with {max_workers} parallel workers")
        
        # Split documents into chunks for parallel processing
        chunk_size = max(10, len(documents) // max_workers)
        chunks = [documents[i:i + chunk_size] for i in range(0, len(documents), chunk_size)]
        
        processed_docs = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all chunks for processing
            future_to_chunk = {
                executor.submit(self._validate_documents, chunk): i 
                for i, chunk in enumerate(chunks)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                chunk_idx = future_to_chunk[future]
                try:
                    chunk_docs = future.result()
                    processed_docs.extend(chunk_docs)
                    logger.info(f"Completed processing chunk {chunk_idx + 1}/{len(chunks)}")
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk_idx}: {e}")
        
        logger.info(f"Parallel processing completed: {len(processed_docs)} documents ready")
        return processed_docs
    
    def _validate_documents(self, documents: List[Document]) -> List[Document]:
        """Validate and clean documents (used in parallel processing)"""
        valid_docs = []
        for doc in documents:
            if doc.page_content and doc.page_content.strip():
                valid_docs.append(doc)
        return valid_docs
    
    def vector_store_exists(self) -> bool:
        """Check if vector store exists"""
        index_file = self.vector_store_path / "index.faiss"
        return index_file.exists()
    
    def load_existing_vector_store(self) -> Optional[FAISS]:
        """Load existing vector store if available"""
        if not self.vector_store_exists():
            return None
        
        try:
            vector_store = FAISS.load_local(
                str(self.vector_store_path), 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info(f"Loaded existing vector store from {self.vector_store_path}")
            return vector_store
        except Exception as e:
            logger.error(f"Failed to load existing vector store: {e}")
            return None
    
    def process_dataframe(self, df: pd.DataFrame, 
                         source_name: str = "dataframe",
                         source_info: str = "",
                         initial_batch_size: int = 100,
                         force_rebuild: bool = False) -> Tuple[FAISS, Dict[str, Any]]:
        """
        Process DataFrame and return vector store with processing stats
        
        Args:
            df: Input DataFrame with query data
            source_name: Name/identifier for the data source
            source_info: Additional info about source (file path, query, etc.)
            initial_batch_size: Size of initial synchronous batch
            force_rebuild: Force complete rebuild ignoring existing data
            
        Returns:
            Tuple of (vector_store, processing_stats)
        """
        logger.info(f"Processing DataFrame: {len(df)} rows from {source_name}")
        
        # Calculate data hash for change detection
        data_hash = self._calculate_data_hash(df, source_info)
        
        # Check if we've already processed this exact data
        existing_source = None
        for source in self.status.get('processed_sources', []):
            if source['name'] == source_name and source['hash'] == data_hash:
                existing_source = source
                break
        
        if existing_source and not force_rebuild:
            logger.info(f"Data unchanged for {source_name}, loading existing vector store")
            vector_store = self.load_existing_vector_store()
            if vector_store:
                return vector_store, {
                    "total_processed": existing_source['row_count'],
                    "processing_time": 0,
                    "new_documents": 0,
                    "cache_hit": True
                }
        
        # Process the data
        start_time = time.time()
        
        # Create documents with composite embeddings
        documents = self._create_documents_from_dataframe(df, source_name)
        if not documents:
            raise ValueError("No valid documents created from DataFrame")
        
        # Process initial batch synchronously (user waits)
        initial_batch = documents[:initial_batch_size]
        logger.info(f"Processing initial batch of {len(initial_batch)} documents synchronously")
        
        batch_start = time.time()
        vector_store = self._process_batch_embeddings(initial_batch)
        initial_time = time.time() - batch_start
        
        logger.info(f"Initial batch completed in {initial_time:.1f}s")
        
        # Save vector store after initial batch
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(self.vector_store_path))
        
        # Process remaining documents in background if any
        remaining_docs = documents[initial_batch_size:]
        background_time = 0
        
        if remaining_docs:
            logger.info(f"Processing {len(remaining_docs)} remaining documents in background")
            
            # Use parallel processing for large batches
            bg_start = time.time()
            if len(remaining_docs) > 100:
                remaining_docs = self._process_batch_parallel(remaining_docs)
            
            # Add remaining documents in batches
            batch_size = 20
            for i in range(0, len(remaining_docs), batch_size):
                batch = remaining_docs[i:i + batch_size]
                
                texts = [doc.page_content for doc in batch]
                metadatas = [doc.metadata for doc in batch]
                
                vector_store.add_texts(texts=texts, metadatas=metadatas)
                
                if i % 100 == 0:  # Log progress every 100 documents
                    logger.info(f"Background processing: {i + len(batch)}/{len(remaining_docs)} documents")
            
            # Save updated vector store
            vector_store.save_local(str(self.vector_store_path))
            background_time = time.time() - bg_start
            logger.info(f"Background processing completed in {background_time:.1f}s")
        
        # Update status
        total_time = time.time() - start_time
        
        # Update or add source tracking
        source_record = {
            "name": source_name,
            "hash": data_hash,
            "row_count": len(df),
            "document_count": len(documents),
            "last_processed": datetime.now().isoformat(),
            "source_info": source_info
        }
        
        # Remove old record for this source if exists
        self.status['processed_sources'] = [
            s for s in self.status.get('processed_sources', []) 
            if s['name'] != source_name
        ]
        self.status['processed_sources'].append(source_record)
        self.status['total_processed'] = len(documents)
        self.status['vector_store_exists'] = True
        self._save_status()
        
        processing_stats = {
            "total_processed": len(documents),
            "processing_time": total_time,
            "initial_batch_time": initial_time,
            "background_time": background_time,
            "new_documents": len(documents),
            "cache_hit": False
        }
        
        logger.info(f"Processing completed: {len(documents)} documents in {total_time:.1f}s")
        return vector_store, processing_stats
    
    def get_processing_status(self) -> Dict[str, Any]:
        """Get current processing status"""
        return self.status.copy()
    
    def cleanup_old_sources(self, max_sources: int = 10):
        """Clean up old source records to prevent status file from growing too large"""
        sources = self.status.get('processed_sources', [])
        if len(sources) > max_sources:
            # Keep most recent sources
            sources.sort(key=lambda x: x.get('last_processed', ''), reverse=True)
            self.status['processed_sources'] = sources[:max_sources]
            self._save_status()
            logger.info(f"Cleaned up old sources, kept {max_sources} most recent")