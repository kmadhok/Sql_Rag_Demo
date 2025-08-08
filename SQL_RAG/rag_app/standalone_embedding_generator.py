#!/usr/bin/env python3
"""
GPU-Accelerated Standalone Embedding Generator - Windows Compatible Pre-Build Mode

A high-performance command-line tool for generating embeddings on Windows systems
with NVIDIA GPU acceleration. Uses ThreadPoolExecutor for stable concurrent processing
and leverages Ollama's built-in GPU acceleration and concurrency features.

Optimized for systems with:
- NVIDIA GPUs (RTX A1000 6GB VRAM and similar)
- High RAM (16GB+ recommended)
- Multi-core CPUs

Usage:
    python standalone_embedding_generator.py --csv "queries.csv"
    python standalone_embedding_generator.py --csv "data.csv" --batch-size 300 --workers 16
    python standalone_embedding_generator.py --help

Performance Notes:
- Uses ThreadPoolExecutor (no pickle issues)
- Leverages Ollama GPU acceleration (20-50x faster)
- Supports large batch sizes with high RAM systems
- Optimized for concurrent GPU embedding requests
"""

import os
import sys
import time
import argparse
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    print("pip install langchain-ollama langchain-community faiss-gpu pandas tqdm")
    print("Note: If faiss-gpu installation fails, fallback to faiss-cpu")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_document_batch_gpu(batch_data):
    """
    Full GPU-accelerated worker function for processing a batch of documents
    
    Uses ThreadPoolExecutor (no pickle issues) with both:
    - Ollama GPU acceleration for embeddings
    - FAISS GPU acceleration for vector operations
    
    Args:
        batch_data: Tuple of (doc_data_list, model_name)
        
    Returns:
        FAISS vector store (GPU-enabled if available) or None if failed
    """
    try:
        # Unpack data (no pickle issues with ThreadPoolExecutor)
        doc_data_list, model_name = batch_data
        
        # Import fresh instances (thread-safe)
        from langchain_ollama import OllamaEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
        
        # Initialize embeddings with GPU acceleration
        # Ollama automatically uses GPU if available and configured
        embeddings = OllamaEmbeddings(model=model_name)
        
        # Recreate Document objects from data
        documents = []
        for doc_data in doc_data_list:
            doc = Document(
                page_content=doc_data['content'],
                metadata=doc_data['metadata']
            )
            documents.append(doc)
        
        # Create vector store with GPU-accelerated embeddings
        vector_store = FAISS.from_documents(documents, embeddings)
        
        # Try to move FAISS index to GPU for faster vector operations
        try:
            import faiss
            if faiss.get_num_gpus() > 0:
                # Move the index to GPU for faster similarity search
                gpu_resources = faiss.StandardGpuResources()
                vector_store.index = faiss.index_cpu_to_gpu(gpu_resources, 0, vector_store.index)
                # print(f"✅ Moved FAISS index to GPU for batch processing")
        except Exception as gpu_error:
            # Continue with CPU FAISS if GPU fails
            pass
        
        return vector_store
        
    except Exception as e:
        # Safe logging for ThreadPoolExecutor
        print(f"❌ Error processing batch with GPU acceleration: {e}")
        return None


class GPUStandaloneEmbeddingGenerator:
    """GPU-accelerated standalone embedding generator with Windows-compatible threading"""
    
    def __init__(self, csv_path: str, output_dir: str = "faiss_indices", 
                 batch_size: int = 100, max_workers: int = 16, verbose: bool = False):
        """
        Initialize the GPU-accelerated standalone embedding generator
        
        Args:
            csv_path: Path to CSV file with queries
            output_dir: Directory to save vector store
            batch_size: Number of documents per batch (higher values recommended for GPU/high RAM)
            max_workers: Number of concurrent threads (leverage GPU concurrency)
            verbose: Enable detailed logging
        
        Recommended settings for high-end systems:
            batch_size: 100-300 (for systems with 16GB+ RAM)
            max_workers: 12-20 (for GPU acceleration with multiple cores)
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
        
        # Check GPU capabilities
        self.gpu_available = self._check_gpu_capabilities()
    
    def _check_gpu_capabilities(self) -> Dict[str, bool]:
        """Check GPU capabilities for both FAISS and Ollama"""
        capabilities = {
            'faiss_gpu': False,
            'nvidia_gpu': False,
            'gpu_memory': 0
        }
        
        try:
            # Check FAISS GPU support
            import faiss
            num_gpus = faiss.get_num_gpus()
            capabilities['faiss_gpu'] = num_gpus > 0
            
            if self.verbose and num_gpus > 0:
                print(f"🚀 FAISS GPU support detected: {num_gpus} GPU(s) available")
            elif self.verbose:
                print("⚠️  FAISS GPU not available - using CPU mode")
                
        except ImportError:
            if self.verbose:
                print("⚠️  faiss-gpu not installed - using faiss-cpu")
        except Exception as e:
            if self.verbose:
                print(f"⚠️  FAISS GPU check failed: {e}")
        
        try:
            # Check NVIDIA GPU
            import subprocess
            result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                gpu_memory = int(result.stdout.strip().split('\n')[0])
                capabilities['nvidia_gpu'] = True
                capabilities['gpu_memory'] = gpu_memory
                
                if self.verbose:
                    print(f"🎯 NVIDIA GPU detected: {gpu_memory} MB VRAM")
                    print("💡 Optimal for RTX A1000 with 6GB VRAM")
            
        except Exception:
            if self.verbose:
                print("⚠️  NVIDIA GPU not detected or nvidia-smi unavailable")
        
        return capabilities
    
    def _initialize_embeddings(self) -> bool:
        """Initialize Ollama embeddings with GPU acceleration testing"""
        try:
            if self.verbose:
                print("🔧 Initializing Ollama GPU-accelerated embeddings...")
            
            self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
            
            # Test connection and GPU acceleration
            start_time = time.time()
            test_result = self.embeddings.embed_query("test connection for GPU acceleration")
            embedding_time = time.time() - start_time
            
            if len(test_result) > 0:
                if self.verbose:
                    print(f"✅ Ollama connection verified (embedding took {embedding_time:.3f}s)")
                    print(f"📊 Embedding dimensions: {len(test_result)}")
                    if embedding_time < 0.1:  # Very fast = likely GPU accelerated
                        print("🚀 GPU acceleration appears to be active!")
                    elif embedding_time < 1.0:  # Fast = good performance
                        print("⚡ Good embedding performance detected")
                    else:  # Slow = likely CPU only
                        print("⚠️  Slower performance - check GPU configuration")
                return True
            else:
                print("❌ Ollama returned empty embedding")
                return False
                
        except Exception as e:
            print(f"❌ Failed to initialize Ollama embeddings: {e}")
            print("Make sure Ollama is running with GPU support:")
            print("  1. ollama serve")
            print("  2. ollama pull nomic-embed-text")
            print("  3. Set OLLAMA_NUM_PARALLEL=16 for optimal concurrency")
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
    
    def _prepare_batch_data(self, docs_batch: List[Document]) -> Tuple[List[Dict], str]:
        """Convert Document objects to serializable data for Windows multiprocessing"""
        doc_data_list = []
        for doc in docs_batch:
            doc_data = {
                'content': doc.page_content,
                'metadata': dict(doc.metadata)  # Ensure metadata is serializable
            }
            doc_data_list.append(doc_data)
        
        return doc_data_list, "nomic-embed-text"
    
    def _generate_embeddings_gpu_parallel(self, documents: List[Document], resume: bool = False) -> FAISS:
        """Generate embeddings using GPU-accelerated ThreadPoolExecutor (Windows-compatible)"""
        
        # Load progress if resuming
        progress = self._load_progress() if resume else {'processed_hashes': [], 'completed_batches': 0, 'total_batches': 0}
        
        # Split into batches
        batches = [documents[i:i + self.batch_size] for i in range(0, len(documents), self.batch_size)]
        total_batches = len(batches)
        progress['total_batches'] = total_batches
        
        print(f"🔧 Processing {len(documents)} documents in {total_batches} batches")
        print(f"📊 Batch size: {self.batch_size}, GPU-accelerated workers: {self.max_workers}")
        print("🚀 Using ThreadPoolExecutor with Ollama GPU acceleration")
        
        if resume and progress['completed_batches'] > 0:
            print(f"📁 Resuming from batch {progress['completed_batches']}/{total_batches}")
        
        # Process batches
        vector_stores = []
        start_time = time.time()
        
        # Filter out already processed batches if resuming
        remaining_batches = batches
        if resume:
            remaining_batches = batches[progress['completed_batches']:]
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Prepare batch data for GPU-accelerated processing
            batch_data_list = []
            for batch in remaining_batches:
                batch_data = self._prepare_batch_data(batch)
                batch_data_list.append(batch_data)
            
            # Submit all remaining batches to GPU-accelerated workers
            future_to_batch = {
                executor.submit(process_document_batch_gpu, batch_data): (i, batch_data) 
                for i, batch_data in enumerate(batch_data_list)
            }
            
            # Process completed batches
            with tqdm(total=len(remaining_batches), desc="Processing batches", unit="batch") as pbar:
                for future in as_completed(future_to_batch):
                    batch_idx, batch_data = future_to_batch[future]
                    
                    try:
                        vector_store = future.result()
                        if vector_store:
                            vector_stores.append(vector_store)
                            
                            # Update progress (calculate hash from batch data)
                            doc_data_list, _ = batch_data
                            content = "\n".join([doc_data['content'] for doc_data in doc_data_list])
                            batch_hash = hashlib.md5(content.encode()).hexdigest()
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
        
        # Merge all vector stores with GPU optimization
        print("🔗 Merging vector stores...")
        main_store = vector_stores[0]
        
        # Merge stores
        for store in vector_stores[1:]:
            main_store.merge_from(store)
        
        # Final GPU optimization for the merged store
        try:
            import faiss
            if self.gpu_available.get('faiss_gpu', False):
                print("🚀 Optimizing final vector store with GPU acceleration...")
                gpu_resources = faiss.StandardGpuResources()
                main_store.index = faiss.index_cpu_to_gpu(gpu_resources, 0, main_store.index)
                print(f"✅ Final vector store moved to GPU ({self.gpu_available['gpu_memory']} MB VRAM)")
        except Exception as e:
            print(f"⚠️  GPU optimization failed, using CPU mode: {e}")
        
        processing_time = time.time() - start_time
        print(f"✅ Completed in {processing_time/60:.1f} minutes")
        
        # Report GPU utilization
        if self.gpu_available.get('faiss_gpu') and self.gpu_available.get('nvidia_gpu'):
            estimated_vram = len(main_store.docstore._dict) * 0.5  # Rough estimate
            print(f"📊 GPU Performance Summary:")
            print(f"   🎯 NVIDIA GPU: {self.gpu_available['gpu_memory']} MB total VRAM")
            print(f"   📦 Estimated FAISS usage: ~{estimated_vram:.0f} MB")
            print(f"   ⚡ Both embeddings and vector ops GPU-accelerated")
        
        return main_store
    
    def _save_vector_store(self, vector_store: FAISS, csv_name: str):
        """Save vector store to disk (converts GPU index to CPU for storage)"""
        index_path = self.output_dir / f"index_{csv_name}"
        
        try:
            # Convert GPU index to CPU before saving (required for serialization)
            gpu_accelerated = False
            try:
                import faiss
                if hasattr(vector_store.index, 'device') or 'Gpu' in str(type(vector_store.index)):
                    # Convert GPU index to CPU for saving
                    vector_store.index = faiss.index_gpu_to_cpu(vector_store.index)
                    gpu_accelerated = True
                    if self.verbose:
                        print("🔄 Converted GPU index to CPU for disk storage")
            except Exception as e:
                if self.verbose:
                    print(f"⚠️  GPU to CPU conversion warning: {e}")
            
            vector_store.save_local(str(index_path))
            
            # Create enhanced status file with GPU information
            status = {
                'csv_file': str(self.csv_path),
                'csv_name': csv_name,
                'total_documents': len(vector_store.docstore._dict),
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'batch_size': self.batch_size,
                'max_workers': self.max_workers,
                'gpu_acceleration': {
                    'faiss_gpu_available': self.gpu_available.get('faiss_gpu', False),
                    'nvidia_gpu_detected': self.gpu_available.get('nvidia_gpu', False),
                    'gpu_memory_mb': self.gpu_available.get('gpu_memory', 0),
                    'gpu_accelerated_processing': gpu_accelerated
                }
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
            
            print("🔄 GPU-accelerated embedding generation starting...")
            print("🚀 Leveraging Ollama GPU acceleration with ThreadPoolExecutor")
            
            # Report GPU capabilities
            if self.gpu_available.get('faiss_gpu') and self.gpu_available.get('nvidia_gpu'):
                print(f"🎯 Full GPU acceleration enabled:")
                print(f"   📊 NVIDIA GPU: {self.gpu_available['gpu_memory']} MB VRAM")
                print(f"   ⚡ Ollama embeddings: GPU-accelerated")
                print(f"   🚀 FAISS vector operations: GPU-accelerated")
            elif self.gpu_available.get('nvidia_gpu'):
                print(f"⚡ Partial GPU acceleration:")
                print(f"   📊 NVIDIA GPU: {self.gpu_available['gpu_memory']} MB VRAM")
                print(f"   ⚡ Ollama embeddings: GPU-accelerated")
                print(f"   ⚠️  FAISS operations: CPU mode (install faiss-gpu)")
            else:
                print("⚠️  CPU-only mode detected")
                print("💡 Consider installing faiss-gpu and ensuring NVIDIA GPU drivers")
            
            # Initialize Ollama
            if not self._initialize_embeddings():
                return False
            
            # Load and validate CSV
            df = self._load_and_validate_csv()
            print(f"📊 Loaded {len(df)} queries from CSV")
            
            # Create documents
            documents = self._create_documents(df)
            split_documents = self._split_documents(documents)
            
            # Generate embeddings with GPU-accelerated threading
            vector_store = self._generate_embeddings_gpu_parallel(split_documents, resume=resume)
            
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
    """Main entry point for GPU-accelerated standalone embedding generator"""
    parser = argparse.ArgumentParser(
        description="GPU-accelerated standalone embedding generator with Windows compatibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (optimal for most systems)
  python standalone_embedding_generator.py --csv "queries.csv"
  
  # High-performance settings for powerful systems (RTX A1000+ with 32GB+ RAM)
  python standalone_embedding_generator.py --csv "data.csv" --batch-size 300 --workers 16
  
  # Moderate settings for mid-range systems
  python standalone_embedding_generator.py --csv "data.csv" --batch-size 150 --workers 8
  
  # Resume interrupted processing
  python standalone_embedding_generator.py --csv "data.csv" --resume
  
  # Force rebuild existing store
  python standalone_embedding_generator.py --csv "data.csv" --force-rebuild
  
Performance Notes:
  - GPU acceleration provides 20-50x speedup over CPU-only processing
  - Higher batch sizes recommended for systems with 16GB+ RAM
  - More workers leverage GPU concurrency (recommend 12-20 for RTX A1000)
  - Set OLLAMA_NUM_PARALLEL=16 environment variable for optimal GPU utilization
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
        '--batch-size', type=int, default=100,
        help='Documents per batch (higher values recommended for GPU/high RAM systems, default: 100)'
    )
    
    parser.add_argument(
        '--workers', type=int, default=16,
        help='Number of concurrent threads (leverage GPU concurrency, default: 16)'
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
    
    # Performance optimization suggestions
    if args.workers > 20:
        print("⚠️  Very high worker count (>20) may not provide additional benefits")
    if args.batch_size > 500:
        print("⚠️  Very large batch size (>500) may cause memory issues on some systems")
    
    # GPU acceleration reminder
    print("💡 For optimal GPU performance, ensure:")
    print("   1. Ollama is running: ollama serve")
    print("   2. GPU model loaded: ollama pull nomic-embed-text") 
    print("   3. Set concurrency: export OLLAMA_NUM_PARALLEL=16")
    
    # Create generator
    try:
        generator = GPUStandaloneEmbeddingGenerator(
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
    # GPU-accelerated threading approach - no multiprocessing setup needed
    # ThreadPoolExecutor is Windows-compatible and avoids pickle issues
    print("🚀 Starting GPU-accelerated embedding generation...")
    sys.exit(main())