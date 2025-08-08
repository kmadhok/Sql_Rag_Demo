#!/usr/bin/env python3
"""
Standalone Embedding Generator - Windows Compatible Pre-Build Mode

A completely independent command-line tool for generating embeddings on Windows systems
without Streamlit interference. Uses multiprocessing for Windows-safe parallel processing.

Usage:
    python standalone_embedding_generator.py --csv "queries.csv"
    python standalone_embedding_generator.py --csv "data.csv" --batch-size 15 --workers 4
    python standalone_embedding_generator.py --help
"""

import os
import sys
import time
import argparse
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm

# Import required components
try:
    from data_source_manager import DataSourceManager
    from langchain_ollama import OllamaEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all required packages are installed:")
    print("pip install langchain-ollama langchain-community faiss-cpu pandas tqdm")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StandaloneEmbeddingGenerator:
    """Standalone embedding generator with Windows-compatible multiprocessing"""
    
    def __init__(self, csv_path: str, output_dir: str = "faiss_indices", 
                 batch_size: int = 25, max_workers: int = 4, verbose: bool = False):
        """
        Initialize the standalone embedding generator
        
        Args:
            csv_path: Path to CSV file with queries
            output_dir: Directory to save vector store
            batch_size: Number of documents per batch (lower for less memory usage)
            max_workers: Number of parallel processes
            verbose: Enable detailed logging
        """
        self.csv_path = Path(csv_path)
        self.output_dir = Path(output_dir)
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.verbose = verbose
        
        # Validate inputs
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize components
        self.embeddings = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            length_function=len
        )
        
        # Progress tracking
        self.progress_file = self.output_dir / "progress.json"
        self.processed_hashes = set()
        
        if verbose:
            logger.setLevel(logging.DEBUG)
    
    def _initialize_embeddings(self) -> bool:
        """Initialize Ollama embeddings with connection testing"""
        try:
            if self.verbose:
                print("🔧 Initializing Ollama embeddings...")
            
            self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
            
            # Test connection with a simple embedding
            test_result = self.embeddings.embed_query("test connection")
            if len(test_result) > 0:
                if self.verbose:
                    print("✅ Ollama connection verified")
                return True
            else:
                print("❌ Ollama returned empty embedding")
                return False
                
        except Exception as e:
            print(f"❌ Failed to initialize Ollama embeddings: {e}")
            print("Make sure Ollama is running: ollama serve")
            print("Make sure model is available: ollama pull nomic-embed-text")
            return False
    
    def _load_and_validate_csv(self) -> pd.DataFrame:
        """Load and validate CSV data"""
        try:
            df = pd.read_csv(self.csv_path)
            
            # Validate required columns
            required_cols = ['query']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Check for optional columns and provide defaults
            if 'description' not in df.columns:
                df['description'] = ''
            if 'table' not in df.columns:
                df['table'] = ''
            if 'joins' not in df.columns:
                df['joins'] = ''
            
            # Remove rows with empty queries
            initial_count = len(df)
            df = df[df['query'].notna() & (df['query'].str.strip() != '')]
            final_count = len(df)
            
            if initial_count != final_count:
                print(f"⚠️  Removed {initial_count - final_count} rows with empty queries")
            
            if self.verbose:
                print(f"📊 Loaded {len(df)} valid queries from CSV")
                print(f"Columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            raise
    
    def _create_documents(self, df: pd.DataFrame) -> List[Document]:
        """Create LangChain documents from DataFrame"""
        documents = []
        
        for idx, row in df.iterrows():
            # Create composite content for richer search
            content_parts = [f"Query: {row['query']}"]
            
            if row.get('description') and str(row['description']).strip():
                content_parts.append(f"Description: {row['description']}")
            
            if row.get('table') and str(row['table']).strip():
                content_parts.append(f"Tables: {row['table']}")
            
            if row.get('joins') and str(row['joins']).strip():
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
                    'source': self.csv_path.name
                }
            )
            documents.append(doc)
        
        return documents
    
    def _split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks if needed"""
        if self.verbose:
            print("📄 Splitting documents into chunks...")
        
        split_docs = self.text_splitter.split_documents(documents)
        
        if self.verbose:
            print(f"Created {len(split_docs)} chunks from {len(documents)} documents")
        
        return split_docs
    
    def _calculate_batch_hash(self, docs_batch: List[Document]) -> str:
        """Calculate hash for a batch of documents"""
        content = "\n".join([doc.page_content for doc in docs_batch])
        return hashlib.md5(content.encode()).hexdigest()
    
    def _load_progress(self) -> Dict:
        """Load processing progress from file"""
        if self.progress_file.exists():
            try:
                import json
                with open(self.progress_file, 'r') as f:
                    progress = json.load(f)
                    self.processed_hashes = set(progress.get('processed_hashes', []))
                    return progress
            except Exception as e:
                if self.verbose:
                    print(f"⚠️  Could not load progress file: {e}")
        
        return {'processed_hashes': [], 'completed_batches': 0, 'total_batches': 0}
    
    def _save_progress(self, progress: Dict):
        """Save processing progress to file"""
        try:
            import json
            progress['processed_hashes'] = list(self.processed_hashes)
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f)
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Could not save progress: {e}")
    
    def _process_document_batch(self, docs_batch: List[Document]) -> Optional[FAISS]:
        """Process a single batch of documents - Windows-safe function"""
        try:
            # Re-initialize embeddings in this process
            embeddings = OllamaEmbeddings(model="nomic-embed-text")
            
            # Create vector store from batch
            vector_store = FAISS.from_documents(docs_batch, embeddings)
            return vector_store
            
        except Exception as e:
            print(f"❌ Error processing batch: {e}")
            return None
    
    def _generate_embeddings_parallel(self, documents: List[Document], resume: bool = False) -> FAISS:
        """Generate embeddings using Windows-compatible multiprocessing"""
        
        # Load progress if resuming
        progress = self._load_progress() if resume else {'processed_hashes': [], 'completed_batches': 0, 'total_batches': 0}
        
        # Split into batches
        batches = [documents[i:i + self.batch_size] for i in range(0, len(documents), self.batch_size)]
        total_batches = len(batches)
        progress['total_batches'] = total_batches
        
        print(f"🔧 Processing {len(documents)} documents in {total_batches} batches")
        print(f"📊 Batch size: {self.batch_size}, Workers: {self.max_workers}")
        
        if resume and progress['completed_batches'] > 0:
            print(f"📁 Resuming from batch {progress['completed_batches']}/{total_batches}")
        
        # Process batches
        vector_stores = []
        start_time = time.time()
        
        # Filter out already processed batches if resuming
        remaining_batches = batches
        if resume:
            remaining_batches = batches[progress['completed_batches']:]
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all remaining batches
            future_to_batch = {
                executor.submit(self._process_document_batch, batch): (i, batch) 
                for i, batch in enumerate(remaining_batches)
            }
            
            # Process completed batches
            with tqdm(total=len(remaining_batches), desc="Processing batches", unit="batch") as pbar:
                for future in as_completed(future_to_batch):
                    batch_idx, batch = future_to_batch[future]
                    
                    try:
                        vector_store = future.result()
                        if vector_store:
                            vector_stores.append(vector_store)
                            
                            # Update progress
                            batch_hash = self._calculate_batch_hash(batch)
                            self.processed_hashes.add(batch_hash)
                            progress['completed_batches'] += 1
                            
                            # Save progress periodically
                            if progress['completed_batches'] % 5 == 0:
                                self._save_progress(progress)
                            
                            # Update progress bar with timing info
                            elapsed = time.time() - start_time
                            if progress['completed_batches'] > 0:
                                avg_time = elapsed / progress['completed_batches']
                                remaining = total_batches - progress['completed_batches']
                                eta = avg_time * remaining
                                pbar.set_postfix({
                                    'ETA': f"{eta/60:.1f}m",
                                    'Completed': f"{progress['completed_batches']}/{total_batches}"
                                })
                            
                        else:
                            print(f"❌ Failed to process batch {batch_idx + 1}")
                    
                    except Exception as e:
                        print(f"❌ Error in batch {batch_idx + 1}: {e}")
                    
                    pbar.update(1)
        
        # Save final progress
        self._save_progress(progress)
        
        if not vector_stores:
            raise RuntimeError("No vector stores were created successfully")
        
        # Merge all vector stores
        print("🔗 Merging vector stores...")
        main_store = vector_stores[0]
        
        for store in vector_stores[1:]:
            main_store.merge_from(store)
        
        processing_time = time.time() - start_time
        print(f"✅ Completed in {processing_time/60:.1f} minutes")
        
        return main_store
    
    def _save_vector_store(self, vector_store: FAISS, csv_name: str):
        """Save vector store to disk"""
        index_path = self.output_dir / f"index_{csv_name}"
        
        try:
            vector_store.save_local(str(index_path))
            
            # Create status file
            status = {
                'csv_file': str(self.csv_path),
                'csv_name': csv_name,
                'total_documents': len(vector_store.docstore._dict),
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'batch_size': self.batch_size,
                'max_workers': self.max_workers
            }
            
            import json
            status_file = self.output_dir / f"status_{csv_name}.json"
            with open(status_file, 'w') as f:
                json.dump(status, f, indent=2)
            
            print(f"📁 Vector store saved to: {index_path}")
            print(f"📄 Status saved to: {status_file}")
            
        except Exception as e:
            print(f"❌ Error saving vector store: {e}")
            raise
    
    def generate(self, resume: bool = False, force_rebuild: bool = False) -> bool:
        """
        Generate embeddings from CSV file
        
        Args:
            resume: Resume interrupted processing
            force_rebuild: Rebuild even if vector store exists
            
        Returns:
            True if successful, False otherwise
        """
        try:
            csv_name = self.csv_path.stem
            index_path = self.output_dir / f"index_{csv_name}"
            
            # Check if vector store already exists
            if index_path.exists() and not force_rebuild and not resume:
                print(f"✅ Vector store already exists: {index_path}")
                print("Use --force-rebuild to rebuild or --resume to continue interrupted processing")
                return True
            
            print("🔄 Windows-optimized embedding generation starting...")
            
            # Initialize Ollama
            if not self._initialize_embeddings():
                return False
            
            # Load and validate CSV
            df = self._load_and_validate_csv()
            print(f"📊 Loaded {len(df)} queries from CSV")
            
            # Create documents
            documents = self._create_documents(df)
            split_documents = self._split_documents(documents)
            
            # Generate embeddings with multiprocessing
            vector_store = self._generate_embeddings_parallel(split_documents, resume=resume)
            
            # Save vector store
            self._save_vector_store(vector_store, csv_name)
            
            # Clean up progress file on successful completion
            if self.progress_file.exists():
                self.progress_file.unlink()
            
            print("✅ All embeddings generated successfully!")
            print(f"⏱️  Total documents processed: {len(vector_store.docstore._dict)}")
            print("🚀 You can now run 'streamlit run app.py'")
            
            return True
            
        except KeyboardInterrupt:
            print("\n⏹️  Processing interrupted by user")
            print("Use --resume flag to continue from where you left off")
            return False
        except Exception as e:
            print(f"❌ Error during generation: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False


def main():
    """Main entry point for standalone embedding generator"""
    parser = argparse.ArgumentParser(
        description="Windows-compatible standalone embedding generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python standalone_embedding_generator.py --csv "queries.csv"
  
  # Custom settings for large datasets
  python standalone_embedding_generator.py --csv "data.csv" --batch-size 15 --workers 4
  
  # Resume interrupted processing
  python standalone_embedding_generator.py --csv "data.csv" --resume
  
  # Force rebuild existing store
  python standalone_embedding_generator.py --csv "data.csv" --force-rebuild
        """
    )
    
    parser.add_argument(
        '--csv', required=True,
        help='Path to CSV file containing queries'
    )
    
    parser.add_argument(
        '--output', default='faiss_indices',
        help='Output directory for vector store (default: faiss_indices)'
    )
    
    parser.add_argument(
        '--batch-size', type=int, default=25,
        help='Documents per batch (lower = less memory, default: 25)'
    )
    
    parser.add_argument(
        '--workers', type=int, default=4,
        help='Number of parallel processes (default: 4)'
    )
    
    parser.add_argument(
        '--resume', action='store_true',
        help='Resume interrupted processing'
    )
    
    parser.add_argument(
        '--force-rebuild', action='store_true',
        help='Rebuild even if vector store exists'
    )
    
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable detailed output'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not Path(args.csv).exists():
        print(f"❌ CSV file not found: {args.csv}")
        return 1
    
    if args.batch_size < 1:
        print("❌ Batch size must be at least 1")
        return 1
    
    if args.workers < 1:
        print("❌ Number of workers must be at least 1")
        return 1
    
    # Windows-specific warnings
    if os.name == 'nt':  # Windows
        if args.workers > 6:
            print("⚠️  High worker count on Windows may cause memory issues")
        if args.batch_size > 50:
            print("⚠️  Large batch size on Windows may cause performance issues")
    
    # Create generator
    try:
        generator = StandaloneEmbeddingGenerator(
            csv_path=args.csv,
            output_dir=args.output,
            batch_size=args.batch_size,
            max_workers=args.workers,
            verbose=args.verbose
        )
        
        # Generate embeddings
        success = generator.generate(
            resume=args.resume,
            force_rebuild=args.force_rebuild
        )
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Required for Windows multiprocessing
    import multiprocessing
    multiprocessing.set_start_method('spawn', force=True)
    
    sys.exit(main())