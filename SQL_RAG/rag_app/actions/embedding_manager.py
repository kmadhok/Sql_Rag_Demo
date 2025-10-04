import os
import json
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from langchain_community.vectorstores import FAISS
from utils.embedding_provider import get_embedding_function
from langchain.schema.document import Document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("embedding_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmbeddingManager:
    """Manages embedding generation outside of Streamlit's context"""
    
    def __init__(self, vector_store_path: str, status_file_path: str):
        """
        Initialize the embedding manager
        
        Args:
            vector_store_path: Path to store FAISS index files
            status_file_path: Path to store embedding status JSON
        """
        self.vector_store_path = Path(vector_store_path)
        self.status_file_path = Path(status_file_path)
        self.lock = threading.Lock()
        self._initialize_status()
        
        # Initialize embeddings via provider factory (Ollama or OpenAI)
        self.embedding_function = get_embedding_function()
        logger.info(
            f"EmbeddingManager initialized. Vector store path: {vector_store_path}"
        )
    
    def _initialize_status(self) -> None:
        """Initialize or load existing status file"""
        if self.status_file_path.exists():
            try:
                with open(self.status_file_path, 'r') as f:
                    self.status = json.load(f)
                logger.info(f"Loaded existing status file: {self.status_file_path}")
            except json.JSONDecodeError:
                logger.warning(f"Could not decode status file. Creating new status.")
                self._create_new_status()
        else:
            logger.info(f"No status file found. Creating new status.")
            self._create_new_status()
    
    def _create_new_status(self) -> None:
        """Create a new status dictionary with default values"""
        self.status = {
            "is_complete": False,
            "background_task_running": False,
            "processed_queries": 0,
            "total_queries": 0,
            "current_batch": 0,
            "total_batches": 0,
            "batches_complete": [],
            "last_updated": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
            "vector_store_exists": False,
            "error": None
        }
        self._save_status()
    
    def _save_status(self) -> None:
        """Save current status to file with lock protection"""
        with self.lock:
            self.status["last_updated"] = datetime.now().isoformat()
            try:
                # Ensure directory exists
                self.status_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write status to file with pretty formatting
                with open(self.status_file_path, 'w') as f:
                    json.dump(self.status, f, indent=2)
                logger.debug(f"Status saved to {self.status_file_path}")
            except Exception as e:
                logger.error(f"Failed to save status file: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current embedding status"""
        with self.lock:
            return self.status.copy()
    
    def vector_store_exists(self) -> bool:
        """Check if vector store exists at the specified path"""
        index_file = self.vector_store_path / "index.faiss"
        return index_file.exists()
    
    def process_initial_batch(self, df: pd.DataFrame, 
                             chunk_size: int = 100) -> Tuple[Any, List[Document]]:
        """
        Process initial batch of queries and build vector store
        
        Args:
            df: DataFrame containing 'query' and 'description' columns
            embedding_function: LangChain embedding function
            chunk_size: Number of documents to process in initial batch
            
        Returns:
            Tuple of (vector_store, documents)
        """
        logger.info(f"Processing initial batch of {chunk_size} documents from DataFrame with {len(df)} total rows")
        print(f"🔍 DataFrame columns: {list(df.columns)}")
        print(f"🔍 DataFrame shape: {df.shape}")
        
        # Set status
        with self.lock:
            self.status["is_complete"] = False
            self.status["background_task_running"] = True
            self.status["processed_queries"] = 0
            self.status["total_queries"] = len(df)
            self.status["current_batch"] = 0
            self.status["total_batches"] = (len(df) - chunk_size) // 1000 + 1 if len(df) > chunk_size else 0
            self.status["batches_complete"] = []
            self.status["error"] = None
            self._save_status()
        
        # Process initial batch
        initial_batch = df.head(chunk_size)
        print(f"🔍 Initial batch size: {len(initial_batch)} rows")
        documents = []
        
        print(f"🔄 Creating documents from initial batch...")
        for i, (_, row) in enumerate(initial_batch.iterrows()):
            if i % 10 == 0:  # Progress every 10 items
                print(f"🔄 Processing document {i+1}/{len(initial_batch)}")
                
            query = row['query'] if 'query' in row else ''
            description = row.get('description', '') if 'description' in df.columns else ''
            
            if pd.notna(query) and isinstance(query, str) and query.strip():
                doc = Document(
                    page_content=f"SQL QUERY: {query}\n\nDESCRIPTION: {description}",
                    metadata={
                        "source": str(row.get('query_id', f'row_{i}')),
                        "query": query,
                        "description": description
                    }
                )
                documents.append(doc)
        
        logger.info(f"Created {len(documents)} documents from initial batch")
        print(f"✅ Created {len(documents)} documents from initial batch")
        
        try:
            # Create vector store with initial documents
            if len(documents) > 0:
                print(f"🔄 Creating FAISS vector store with {len(documents)} documents...")
                print(f"🔍 Using embedding function: {type(self.embedding_function).__name__}")
                
                start_embed = time.time()
                
                # Process in smaller batches to avoid Ollama timeouts
                batch_size = 10
                if len(documents) <= batch_size:
                    # Small batch - process all at once
                    vector_store = FAISS.from_documents(documents, self.embedding_function)
                else:
                    # Large batch - process in chunks
                    print(f"🔄 Processing {len(documents)} documents in batches of {batch_size}...")
                    
                    # Create first batch
                    first_batch = documents[:batch_size]
                    vector_store = FAISS.from_documents(first_batch, self.embedding_function)
                    print(f"✅ Created initial vector store with {len(first_batch)} documents")
                    
                    # Add remaining documents in batches
                    remaining = documents[batch_size:]
                    for i in range(0, len(remaining), batch_size):
                        batch = remaining[i:i + batch_size]
                        print(f"🔄 Adding batch {i//batch_size + 2}: {len(batch)} documents...")
                        
                        # Extract texts and metadata
                        texts = [doc.page_content for doc in batch]
                        metadatas = [doc.metadata for doc in batch]
                        
                        # Add to existing vector store
                        vector_store.add_texts(texts=texts, metadatas=metadatas)
                
                embed_time = time.time() - start_embed
                print(f"⏱️ FAISS creation took {embed_time:.1f} seconds")
                
                # Ensure directory exists
                print(f"🔄 Saving vector store to {self.vector_store_path}")
                self.vector_store_path.mkdir(parents=True, exist_ok=True)
                
                # Save vector store
                start_save = time.time()
                vector_store.save_local(str(self.vector_store_path))
                save_time = time.time() - start_save
                print(f"⏱️ Vector store save took {save_time:.1f} seconds")
                logger.info(f"Saved vector store to {self.vector_store_path}")
                
                # Update status
                with self.lock:
                    self.status["processed_queries"] = len(initial_batch)
                    self.status["vector_store_exists"] = True
                    self._save_status()
                
                print(f"✅ Vector store created and saved successfully!")
                return vector_store, documents
            else:
                logger.warning("No valid documents found in initial batch")
                with self.lock:
                    self.status["error"] = "No valid documents found in initial batch"
                    self._save_status()
                return None, []
                
        except Exception as e:
            error_msg = f"Error creating vector store: {str(e)}"
            logger.error(error_msg)
            with self.lock:
                self.status["error"] = error_msg
                self.status["background_task_running"] = False
                self._save_status()
            raise
    
    def start_background_processing(self, df: pd.DataFrame, 
                                   chunk_size: int = 100, batch_size: int = 1000) -> None:
        """
        Start background processing of remaining documents
        
        Args:
            df: DataFrame containing 'query' and 'description' columns
            embedding_function: LangChain embedding function
            chunk_size: Number of documents already processed in initial batch
            batch_size: Size of batches to process in background
        """
        if len(df) <= chunk_size:
            logger.info("No remaining documents to process")
            with self.lock:
                self.status["is_complete"] = True
                self.status["background_task_running"] = False
                self._save_status()
            return
        
        remaining_df = df.iloc[chunk_size:]
        logger.info(f"Starting background processing for {len(remaining_df)} remaining documents")
        
        # Set status
        with self.lock:
            self.status["background_task_running"] = True
            self.status["total_queries"] = len(df)
            self.status["processed_queries"] = chunk_size
            self.status["total_batches"] = (len(remaining_df) - 1) // batch_size + 1
            self._save_status()
        
        # Start background thread
        thread = threading.Thread(
            target=self._process_remaining_in_background,
            args=(remaining_df, batch_size),
            daemon=True
        )
        thread.start()
        logger.info(f"Background thread started with ID: {thread.ident}")
    
    def _process_remaining_in_background(self, df: pd.DataFrame,
                                        batch_size: int = 1000) -> None:
        """
        Process remaining documents in background
        
        Args:
            df: DataFrame containing remaining documents
            embedding_function: LangChain embedding function
            batch_size: Size of batches to process
        """
        try:
            # Process in batches
            total_rows = len(df)
            batches = range(0, total_rows, batch_size)
            
            for i, batch_start in enumerate(batches):
                batch_id = i + 1  # 1-based index for batch ID
                batch_end = min(batch_start + batch_size, total_rows)
                batch = df.iloc[batch_start:batch_end]
                
                # Log batch processing
                logger.info(f"Processing batch {batch_id}/{len(batches)} ({batch_start} to {batch_end-1})")
                
                try:
                    # Build documents for this batch
                    documents = []
                    for _, row in batch.iterrows():
                        query = row['query']
                        description = row.get('description', '')
                        
                        if pd.notna(query) and isinstance(query, str) and query.strip():
                            doc = Document(
                                page_content=f"SQL QUERY: {query}\n\nDESCRIPTION: {description}",
                                metadata={
                                    "source": str(row.get('query_id', 'unknown')),
                                    "query": query,
                                    "description": description
                                }
                            )
                            documents.append(doc)
                    
                    # Load existing vector store
                    if len(documents) > 0:
                        vector_store = FAISS.load_local(str(self.vector_store_path), self.embedding_function)
                        
                        # Add documents from this batch
                        vector_store.add_documents(documents)
                        vector_store.save_local(str(self.vector_store_path))
                        
                        # Update status
                        with self.lock:
                            self.status["processed_queries"] += len(batch)
                            self.status["current_batch"] = batch_id
                            self.status["batches_complete"].append(batch_id)
                            self._save_status()
                        
                        logger.info(f"Added {len(documents)} documents from batch {batch_id}")
                    else:
                        logger.warning(f"No valid documents found in batch {batch_id}")
                    
                    # Sleep a bit to avoid overwhelming the system
                    time.sleep(0.5)
                    
                except Exception as e:
                    error_msg = f"Error processing batch {batch_id}: {str(e)}"
                    logger.error(error_msg)
                    with self.lock:
                        self.status["error"] = error_msg
                        self._save_status()
            
            # Mark as complete
            logger.info("Background processing completed successfully")
            with self.lock:
                self.status["is_complete"] = True
                self.status["background_task_running"] = False
                self._save_status()
                
        except Exception as e:
            error_msg = f"Error in background processing thread: {str(e)}"
            logger.error(error_msg)
            with self.lock:
                self.status["error"] = error_msg
                self.status["background_task_running"] = False
                self._save_status()
    
    def cancel_background_processing(self) -> None:
        """
        Cancel background processing (note: this doesn't actually kill the thread,
        but signals that it should be considered cancelled)
        """
        with self.lock:
            self.status["background_task_running"] = False
            self.status["error"] = "Background processing cancelled by user"
            self._save_status()
        logger.info("Background processing cancelled by user")
