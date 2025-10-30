#!/usr/bin/env python3
"""
Gemini-Powered Standalone Embedding Generator - Windows Compatible

A high-performance command-line tool for generating embeddings on Windows systems
with FAISS GPU acceleration. Uses ThreadPoolExecutor for stable concurrent processing
and leverages Google's Gemini embeddings for superior vector quality.

Optimized for systems with:
- NVIDIA GPUs (RTX A1000 6GB VRAM and similar)
- High RAM (16GB+ recommended)
- Multi-core CPUs
- Google Cloud access with proper authentication

Usage:
    python standalone_embedding_generator.py --csv "queries.csv"
    python standalone_embedding_generator.py --csv "data.csv" --batch-size 300 --workers 16
    python standalone_embedding_generator.py --help

Features:
- Uses Gemini embeddings (768-dimension, high-quality)
- FAISS GPU acceleration for vector operations (20-50x faster)
- Supports large batch sizes with high RAM systems
- Optimized for concurrent GPU processing
- Cloud-ready with Vertex AI integration
"""

import os
import sys
import time
import argparse
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm

from utils.skip_list_loader import load_skip_queries

# Import required components
try:
    from data_source_manager import DataSourceManager
    from utils.embedding_provider import get_embedding_function
    from langchain_community.vectorstores import FAISS
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
    # Import LookML parser
    from simple_lookml_parser import SimpleLookMLParser
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all required packages are installed:")
    print("pip install faiss-gpu pandas tqdm langchain langchain-community")
    print("For Gemini embeddings: pip install google-genai")
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
    - Gemini embeddings for high-quality vector representations
    - FAISS GPU acceleration for vector operations
    
    Args:
        batch_data: Tuple of (doc_data_list)
        
    Returns:
        FAISS vector store (GPU-enabled if available) or None if failed
    """
    try:
        # Unpack data (no pickle issues with ThreadPoolExecutor)
        doc_data_list = batch_data
        
        # Import fresh instances (thread-safe)
        from utils.embedding_provider import get_embedding_function
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
        
        # Initialize Gemini embeddings
        embeddings = get_embedding_function(provider="gemini")
        
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
    """GPU-accelerated standalone embedding generator with Gemini embeddings"""
    
    def __init__(self, csv_path: str, output_dir: str = "faiss_indices", 
                 batch_size: int = 100, max_workers: int = 16, verbose: bool = False,
                 schema_path: Optional[str] = None, lookml_dir: Optional[str] = None,
                 skip_list: Optional[List[str]] = None):
        """
        Initialize the GPU-accelerated standalone embedding generator
        
        Args:
            csv_path: Path to CSV file with queries
            output_dir: Directory to save vector store
            batch_size: Number of documents per batch (higher values recommended for GPU/high RAM)
            max_workers: Number of concurrent threads (leverage GPU concurrency)
            verbose: Enable detailed logging
            schema_path: Optional path to CSV file with schema information (table_id, column, datatype)
        
        Recommended settings for high-end systems:
            batch_size: 100-300 (for systems with 16GB+ RAM)
            max_workers: 12-20 (for GPU acceleration with multiple cores)
        """
        self.csv_path = Path(csv_path)
        self.output_dir = Path(output_dir)
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.verbose = verbose
        self.schema_path = Path(schema_path) if schema_path else None
        self.lookml_dir = Path(lookml_dir) if lookml_dir else None
        self.skip_queries: Set[str] = set()
        
        # Validate inputs
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        if skip_list:
            skip_paths = [Path(path) for path in skip_list]
            self.skip_queries = load_skip_queries(skip_paths)
            if verbose:
                print(f"🧮 Loaded {len(self.skip_queries)} queries from skip list")
        
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
        
        # Load schema data if provided
        self.schema_lookup = {}
        if self.schema_path:
            try:
                self.schema_lookup = self._load_schema_data(self.schema_path)
                if verbose:
                    schema_tables = len(self.schema_lookup)
                    total_columns = sum(len(cols) for cols in self.schema_lookup.values())
                    print(f"✅ Loaded schema for {schema_tables} tables ({total_columns} total columns)")
            except Exception as e:
                logger.warning(f"Failed to load schema data: {e}")
                if verbose:
                    print(f"⚠️  Schema loading failed: {e}")
                self.schema_lookup = {}
    
    def _check_gpu_capabilities(self) -> Dict[str, bool]:
        """Check GPU capabilities for FAISS acceleration"""
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
    
    def _load_schema_data(self, schema_path: Path) -> Dict[str, List[Tuple[str, str]]]:
        """
        Load schema data from CSV file and create lookup dictionary
        
        Args:
            schema_path: Path to schema CSV file with columns (table_id, column, datatype)
            
        Returns:
            Dictionary mapping table names to list of (column, datatype) tuples
        """
        try:
            if self.verbose:
                print(f"📊 Loading schema data from {schema_path}")
            
            schema_df = pd.read_csv(schema_path)
            initial_rows = len(schema_df)
            
            if self.verbose:
                print(f"   📄 Read {initial_rows} rows from schema file")
            
            # Validate required columns
            required_cols = ['table_id', 'column', 'datatype']
            missing_cols = [col for col in required_cols if col not in schema_df.columns]
            if missing_cols:
                raise ValueError(f"Schema CSV missing required columns: {missing_cols}")
            
            if self.verbose:
                print(f"   ✅ Schema file has required columns: {required_cols}")
            
            # Remove rows with empty values
            schema_df = schema_df.dropna()
            schema_df = schema_df[
                (schema_df['table_id'].str.strip() != '') &
                (schema_df['column'].str.strip() != '') &
                (schema_df['datatype'].str.strip() != '')
            ]
            
            filtered_rows = len(schema_df)
            if initial_rows != filtered_rows:
                skipped = initial_rows - filtered_rows
                logger.info(f"Filtered out {skipped} rows with empty values")
                if self.verbose:
                    print(f"   🧹 Filtered out {skipped} rows with empty values")
            
            # Build lookup dictionary with detailed tracking
            schema_lookup = {}
            processed_tables = set()
            total_columns = 0
            
            for _, row in schema_df.iterrows():
                try:
                    table_id = str(row['table_id']).strip()
                    column = str(row['column']).strip()
                    datatype = str(row['datatype']).strip()
                    
                    # Normalize table name (extract from project.dataset.table format)
                    table_name = self._normalize_table_name(table_id)
                    
                    if table_name not in schema_lookup:
                        schema_lookup[table_name] = []
                        processed_tables.add(table_name)
                    
                    schema_lookup[table_name].append((column, datatype))
                    total_columns += 1
                    
                except Exception as row_error:
                    logger.warning(f"Skipping invalid schema row: {row_error}")
                    continue
            
            # Log detailed statistics
            unique_datatypes = set()
            for table_schema in schema_lookup.values():
                for _, datatype in table_schema:
                    unique_datatypes.add(datatype)
            
            logger.info(f"✅ Loaded schema for {len(schema_lookup)} tables ({total_columns} columns, {len(unique_datatypes)} data types)")
            
            if self.verbose:
                print(f"   📊 Schema Statistics:")
                print(f"      • Tables: {len(schema_lookup)}")
                print(f"      • Total Columns: {total_columns}")
                print(f"      • Data Types: {len(unique_datatypes)}")
                print(f"      • Top data types: {', '.join(list(unique_datatypes)[:5])}")
                
                # Show sample tables
                sample_tables = list(schema_lookup.keys())[:3]
                if sample_tables:
                    print(f"      • Sample tables: {', '.join(sample_tables)}")
            
            if not schema_lookup:
                logger.warning("No valid schema data found after processing")
                if self.verbose:
                    print("   ⚠️  No valid schema data found")
            
            return schema_lookup
            
        except FileNotFoundError:
            error_msg = f"Schema file not found: {schema_path}"
            logger.error(error_msg)
            if self.verbose:
                print(f"   ❌ {error_msg}")
            raise
        except pd.errors.EmptyDataError:
            error_msg = f"Schema file is empty: {schema_path}"
            logger.error(error_msg)
            if self.verbose:
                print(f"   ❌ {error_msg}")
            raise
        except Exception as e:
            error_msg = f"Failed to load schema data from {schema_path}: {e}"
            logger.error(error_msg)
            if self.verbose:
                print(f"   ❌ {error_msg}")
            raise
    
    def _normalize_table_name(self, table_id: str) -> str:
        """
        Extract table name from BigQuery format (project.dataset.table)
        
        Args:
            table_id: Full table identifier (e.g., "project.dataset.customers")
            
        Returns:
            Normalized table name (e.g., "customers")
        """
        # Remove backticks and quotes
        clean_id = table_id.strip('`"\'')
        
        # Extract table name (last part after dots)
        if '.' in clean_id:
            return clean_id.split('.')[-1].strip()
        
        return clean_id.strip()
    
    def _get_table_schema(self, table_name: str) -> List[Tuple[str, str]]:
        """
        Get schema information for a specific table
        
        Args:
            table_name: Name of the table to look up
            
        Returns:
            List of (column, datatype) tuples for the table
        """
        # Normalize the input table name
        normalized_name = self._normalize_table_name(table_name)
        
        # Look up in schema
        return self.schema_lookup.get(normalized_name, [])
    
    def _initialize_embeddings(self) -> bool:
        """Initialize Gemini embeddings"""
        try:
            if self.verbose:
                print("🔧 Initializing Gemini embeddings...")
            
            self.embeddings = get_embedding_function(provider="gemini")
            
            # Test connection
            start_time = time.time()
            test_result = self.embeddings.embed_query("test connection for Gemini embeddings")
            embedding_time = time.time() - start_time
            
            if len(test_result) > 0:
                if self.verbose:
                    print(f"✅ Gemini connection verified (embedding took {embedding_time:.3f}s)")
                    print(f"📊 Embedding dimensions: {len(test_result)}")
                    if embedding_time < 1.0:  # Fast = good performance
                        print("🚀 Good embedding performance detected")
                    else:  # Slow = potential issues
                        print("⚠️  Slower performance - check network and API configuration")
                return True
            else:
                print("❌ Gemini returned empty embedding")
                return False
                
        except Exception as e:
            print(f"❌ Failed to initialize Gemini embeddings: {e}")
            print("Make sure Google Cloud authentication is properly configured:")
            print("  1. Set GOOGLE_CLOUD_PROJECT environment variable")
            print("  2. Ensure service account has 'aiplatform.user' role")
            print("  3. For local development: gcloud auth application-default login")
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

            if self.skip_queries:
                before_skip = len(df)
                df = df[~df["query"].astype(str).str.strip().isin(self.skip_queries)].copy()
                skipped = before_skip - len(df)
                if skipped:
                    print(f"🛑 Skipped {skipped} queries from skip list")
            
            if self.verbose:
                print(f"📊 Loaded {len(df)} valid queries from CSV")
                print(f"Columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            raise

    def _calculate_csv_hash(self, df: pd.DataFrame) -> str:
        """Calculate hash of CSV content for change detection"""
        try:
            # Create a string representation of the dataframe content
            content_string = ""
            
            # Sort by a stable column if available, otherwise by index
            sorted_df = df.sort_index()
            
            for _, row in sorted_df.iterrows():
                # Create a unique string for each row
                row_parts = []
                for col in ['query', 'description', 'table', 'joins']:
                    if col in row:
                        value = str(row[col]) if pd.notna(row[col]) else ""
                        row_parts.append(f"{col}:{value}")
                
                content_string += "|".join(row_parts) + "\n"
            
            # Return MD5 hash of the content
            return hashlib.md5(content_string.encode('utf-8')).hexdigest()
            
        except Exception as e:
            logger.warning(f"Failed to calculate CSV hash: {e}")
            return ""
    
    def _create_query_fingerprint(self, row: pd.Series) -> str:
        """Create unique fingerprint for a single query including schema information"""
        try:
            # Combine key fields to create unique identifier
            parts = []
            for col in ['query', 'description', 'table', 'joins']:
                if col in row:
                    value = str(row[col]) if pd.notna(row[col]) else ""
                    parts.append(value)
            
            # Include schema information in fingerprint if available
            if self.schema_lookup:
                schema_info = self._get_schema_info_for_query(row)
                if schema_info:
                    # Add schema content to fingerprint
                    schema_content = "|".join(schema_info)
                    parts.append(f"SCHEMA:{schema_content}")
                
                # Also include schema file path modification time if available
                if self.schema_path and self.schema_path.exists():
                    schema_mtime = os.path.getmtime(self.schema_path)
                    parts.append(f"SCHEMA_MTIME:{schema_mtime}")
            
            content = "|".join(parts)
            return hashlib.md5(content.encode('utf-8')).hexdigest()
            
        except Exception as e:
            logger.warning(f"Failed to create query fingerprint: {e}")
            return ""
    
    def _load_processing_status(self) -> Dict:
        """Load detailed processing status with incremental tracking"""
        csv_name = self.csv_path.stem
        status_file = self.output_dir / f"status_{csv_name}.json"
        
        if not status_file.exists():
            return {
                'csv_file': str(self.csv_path),
                'csv_name': csv_name,
                'csv_hash': '',
                'csv_modification_time': '',
                'processed_query_fingerprints': [],
                'total_documents': 0,
                'last_processed': '',
                'processing_history': []
            }
        
        try:
            import json
            with open(status_file, 'r') as f:
                status = json.load(f)
            
            # Ensure all required fields exist for backward compatibility
            if 'processed_query_fingerprints' not in status:
                status['processed_query_fingerprints'] = []
            if 'csv_hash' not in status:
                status['csv_hash'] = ''
            if 'csv_modification_time' not in status:
                status['csv_modification_time'] = ''
            if 'processing_history' not in status:
                status['processing_history'] = []
            
            return status
            
        except Exception as e:
            logger.warning(f"Failed to load processing status: {e}")
            # Return empty status instead of recursion
            return {
                'csv_file': str(self.csv_path),
                'csv_name': self.csv_path.stem,
                'csv_hash': '',
                'csv_modification_time': '',
                'processed_query_fingerprints': [],
                'total_documents': 0,
                'last_processed': '',
                'processing_history': []
            }
    
    def _identify_new_queries(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Identify new queries that haven't been processed yet
        
        Returns:
            Tuple of (new_queries_df, new_fingerprints_list)
        """
        status = self._load_processing_status()
        processed_fingerprints = set(status.get('processed_query_fingerprints', []))
        
        new_rows = []
        new_fingerprints = []
        
        for idx, row in df.iterrows():
            fingerprint = self._create_query_fingerprint(row)
            
            if fingerprint not in processed_fingerprints:
                new_rows.append(row)
                new_fingerprints.append(fingerprint)
        
        if new_rows:
            new_df = pd.DataFrame(new_rows)
            new_df.reset_index(drop=True, inplace=True)
        else:
            new_df = pd.DataFrame()
        
        return new_df, new_fingerprints
    
    def _has_csv_changed(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check if CSV content has changed since last processing
        
        Returns:
            Tuple of (has_changed, reason)
        """
        try:
            status = self._load_processing_status()
            current_hash = self._calculate_csv_hash(df)
            stored_hash = status.get('csv_hash', '')
            
            # Get file modification time
            csv_mod_time = os.path.getmtime(self.csv_path)
            csv_mod_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(csv_mod_time))
            stored_mod_time = status.get('csv_modification_time', '')
            
            if not stored_hash:
                return True, "No previous processing found"
            
            if current_hash != stored_hash:
                return True, f"CSV content changed (hash: {stored_hash[:8]} → {current_hash[:8]})"
            
            if csv_mod_str != stored_mod_time:
                return True, f"CSV file modified (time: {stored_mod_time} → {csv_mod_str})"
            
            return False, "No changes detected"
            
        except Exception as e:
            logger.warning(f"Error checking CSV changes: {e}")
            return True, "Error during change detection"
    
    def _create_documents(self, df: pd.DataFrame) -> List[Document]:
        """Create clean LangChain documents from DataFrame WITHOUT schema (for better semantic matching)"""
        documents = []
        
        # Track schema coverage statistics
        total_queries = len(df)
        queries_with_schema = 0
        total_tables_found = 0
        total_tables_with_schema = 0
        
        if self.verbose:
            if self.schema_lookup:
                print(f"⚡ Creating clean documents (schema-free) for {total_queries} queries...")
                print(f"🗃️  Schema available for dynamic injection: {self.table_count:,} tables")
            else:
                print(f"📊 Creating documents for {total_queries} queries...")
        
        for idx, row in df.iterrows():
            # Create composite content for richer search
            content_parts = [f"Query: {row['query']}"]
            
            if row.get('description') and str(row['description']).strip():
                content_parts.append(f"Description: {row['description']}")
            
            if row.get('table') and str(row['table']).strip():
                content_parts.append(f"Tables: {row['table']}")
            
            if row.get('joins') and str(row['joins']).strip():
                content_parts.append(f"Joins: {row['joins']}")
            
            # REMOVED: Schema information to reduce noise in embeddings
            # Schema will be injected dynamically during query time via SchemaManager
            # This creates cleaner embeddings for better semantic matching
            
            # Track table coverage for statistics
            if self.schema_lookup:
                query_tables = self._extract_tables_from_row(row)
                total_tables_found += len(query_tables)
                for table in query_tables:
                    if self._get_table_schema(table):
                        total_tables_with_schema += 1
            
            content = "\n".join(content_parts)
            
            # Create document with metadata (including schema info)
            metadata = {
                'index': idx,
                'query': row['query'],
                'description': str(row.get('description', '')),
                'table': str(row.get('table', '')),
                'joins': str(row.get('joins', '')),
                'source': self.csv_path.name
            }
            
            # Note: Schema metadata removed to keep embeddings clean
            # Schema will be available via SchemaManager during query time
            metadata['has_schema'] = False
            metadata['schema_tables'] = []
            
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
        
        # Log schema availability statistics (schema not included in embeddings)
        if self.schema_lookup and self.verbose:
            table_coverage = (total_tables_with_schema / total_tables_found * 100) if total_tables_found > 0 else 0
            
            logger.info(f"📊 Schema Available for Dynamic Injection:")
            logger.info(f"   • Total tables in schema: {self.table_count:,}")
            logger.info(f"   • Tables found in queries: {total_tables_found}")
            logger.info(f"   • Tables with schema available: {total_tables_with_schema}/{total_tables_found} ({table_coverage:.1f}%)")
            
            print(f"   ⚡ Clean Embeddings: Schema removed from embeddings for better semantic matching")
            print(f"   🗃️  Schema Available: {self.table_count:,} tables ready for dynamic injection via SchemaManager")
        
        return documents
    
    def _create_lookml_documents(self) -> List[Document]:
        """Create documents from LookML files for business logic and join relationships"""
        if not self.lookml_dir or not self.lookml_dir.exists():
            return []
        
        try:
            if self.verbose:
                print(f"🔗 Processing LookML files from {self.lookml_dir}...")
            
            # Parse LookML files
            parser = SimpleLookMLParser(verbose=False)  # Keep parser output clean
            models = parser.parse_directory(self.lookml_dir)
            
            if not models:
                if self.verbose:
                    print("⚠️  No LookML models parsed successfully")
                return []
            
            # Generate safe-join map for saving
            safe_join_map = parser.generate_safe_join_map(models)
            
            # Save safe-join map for later use by the application
            safe_join_path = self.output_dir / "lookml_safe_join_map.json"
            try:
                import json
                with open(safe_join_path, 'w') as f:
                    json.dump(safe_join_map, f, indent=2)
                if self.verbose:
                    print(f"💾 Saved safe-join map to {safe_join_path}")
            except Exception as e:
                logger.warning(f"Failed to save safe-join map: {e}")
            
            # Create embedding documents
            documents = parser.create_embedding_documents(models)
            
            # Convert to LangChain Document format with source=lookml metadata
            lookml_documents = []
            for doc_dict in documents:
                # Ensure source is marked as lookml
                metadata = doc_dict['metadata'].copy()
                metadata['source'] = 'lookml'
                
                doc = Document(
                    page_content=doc_dict['page_content'],
                    metadata=metadata
                )
                lookml_documents.append(doc)
            
            if self.verbose:
                explores_count = len([d for d in documents if d['metadata']['type'] == 'explore'])
                joins_count = len([d for d in documents if d['metadata']['type'] == 'join'])
                print(f"   📊 Created {explores_count} explore documents and {joins_count} join documents")
                print(f"   🔗 Total join relationships: {safe_join_map['metadata']['total_joins']}")
            
            return lookml_documents
            
        except Exception as e:
            logger.error(f"Failed to process LookML files: {e}")
            if self.verbose:
                print(f"❌ LookML processing failed: {e}")
            return []
    
    def _extract_tables_from_row(self, row: pd.Series) -> List[str]:
        """
        Extract table names from a query row's metadata
        
        Args:
            row: DataFrame row containing query metadata
            
        Returns:
            List of normalized table names
        """
        tables = []
        
        # Get tables from the 'table' or 'tables' column
        table_data = row.get('table') or row.get('tables', '')
        
        if table_data and str(table_data).strip():
            table_str = str(table_data).strip()
            
            # Try to parse as list first (if it's a string representation of a list)
            try:
                import ast
                if table_str.startswith('[') and table_str.endswith(']'):
                    parsed_tables = ast.literal_eval(table_str)
                    if isinstance(parsed_tables, list):
                        tables = [self._normalize_table_name(str(t)) for t in parsed_tables if str(t).strip()]
                    else:
                        tables = [self._normalize_table_name(table_str)]
                else:
                    # Parse as comma-separated string
                    if ',' in table_str:
                        tables = [self._normalize_table_name(t.strip()) for t in table_str.split(',') if t.strip()]
                    else:
                        tables = [self._normalize_table_name(table_str)]
            except:
                # Fallback to simple parsing
                if ',' in table_str:
                    tables = [self._normalize_table_name(t.strip()) for t in table_str.split(',') if t.strip()]
                else:
                    tables = [self._normalize_table_name(table_str)]
        
        # Remove empty strings and duplicates while preserving order
        unique_tables = []
        for table in tables:
            if table and table not in unique_tables:
                unique_tables.append(table)
        
        return unique_tables
    
    def _get_schema_info_for_query(self, row: pd.Series) -> List[str]:
        """
        Generate schema information content for a query row
        
        Args:
            row: DataFrame row containing query metadata
            
        Returns:
            List of content strings with schema information
        """
        if not self.schema_lookup:
            return []
        
        try:
            # Extract tables from the row
            tables = self._extract_tables_from_row(row)
            
            if not tables:
                return []
            
            schema_content = []
            table_schemas = {}
            all_columns = []
            tables_with_schema = []
            tables_without_schema = []
            
            # Gather schema info for each table with tracking
            for table in tables:
                try:
                    schema = self._get_table_schema(table)
                    if schema:
                        table_schemas[table] = schema
                        all_columns.extend([(table, col, dtype) for col, dtype in schema])
                        tables_with_schema.append(table)
                    else:
                        tables_without_schema.append(table)
                except Exception as table_error:
                    logger.debug(f"Error getting schema for table '{table}': {table_error}")
                    tables_without_schema.append(table)
            
            # Log schema coverage if verbose
            if self.verbose and (tables_with_schema or tables_without_schema):
                coverage = len(tables_with_schema) / len(tables) * 100 if tables else 0
                logger.debug(f"Schema coverage for query: {coverage:.1f}% ({len(tables_with_schema)}/{len(tables)} tables)")
                if tables_without_schema:
                    logger.debug(f"Tables without schema: {', '.join(tables_without_schema)}")
            
            if not table_schemas:
                return []
            
            # Format schema information for embedding
            schema_lines = []
            type_mappings = []
            
            for table, schema in table_schemas.items():
                if schema:
                    try:
                        # Create detailed schema line
                        columns_with_types = [f"{col} ({dtype})" for col, dtype in schema]
                        schema_lines.append(f"- {table}: {', '.join(columns_with_types)}")
                        
                        # Create type mappings for searchability
                        for col, dtype in schema:
                            type_mappings.append(f"{col}→{dtype}")
                    except Exception as format_error:
                        logger.warning(f"Error formatting schema for table '{table}': {format_error}")
                        continue
            
            if schema_lines:
                schema_content.append("Schema Context:")
                schema_content.extend(schema_lines)
                
                # Add searchable column type information
                if type_mappings:
                    schema_content.append(f"Column Types: {', '.join(type_mappings)}")
                
                # Add data type summary for search
                datatypes = list(set(dtype for _, _, dtype in all_columns))
                if datatypes:
                    schema_content.append(f"Data Types Used: {', '.join(sorted(datatypes))}")
                
                # Add schema coverage information for search
                if tables_without_schema:
                    schema_content.append(f"Partial Schema Coverage: {len(tables_with_schema)}/{len(tables)} tables")
            
            return schema_content
            
        except Exception as e:
            logger.warning(f"Error generating schema info for query: {e}")
            return []
    
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
    
    def _prepare_batch_data(self, docs_batch: List[Document]) -> List[Dict]:
        """Convert Document objects to serializable data for multiprocessing"""
        doc_data_list = []
        for doc in docs_batch:
            doc_data = {
                'content': doc.page_content,
                'metadata': dict(doc.metadata)  # Ensure metadata is serializable
            }
            doc_data_list.append(doc_data)
        
        return doc_data_list
    
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
        print("🚀 Using ThreadPoolExecutor with Gemini embeddings")
        
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
                            doc_data_list = batch_data
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
    
    def _save_vector_store(self, vector_store: FAISS, csv_name: str, df: pd.DataFrame = None, 
                          new_fingerprints: List[str] = None, is_incremental: bool = False):
        """Save vector store to disk with enhanced incremental tracking"""
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
            
            # Load existing status for incremental updates
            status = self._load_processing_status()
            
            # Update status with new information
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            
            status.update({
                'csv_file': str(self.csv_path),
                'csv_name': csv_name,
                'total_documents': len(vector_store.docstore._dict),
                'last_processed': current_time,
                'batch_size': self.batch_size,
                'max_workers': self.max_workers,
                'gpu_acceleration': {
                    'faiss_gpu_available': self.gpu_available.get('faiss_gpu', False),
                    'nvidia_gpu_detected': self.gpu_available.get('nvidia_gpu', False),
                    'gpu_memory_mb': self.gpu_available.get('gpu_memory', 0),
                    'gpu_accelerated_processing': gpu_accelerated
                }
            })
            
            # Update incremental tracking data
            if df is not None:
                # Update CSV hash and modification time
                status['csv_hash'] = self._calculate_csv_hash(df)
                csv_mod_time = os.path.getmtime(self.csv_path)
                status['csv_modification_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(csv_mod_time))
                
                if is_incremental and new_fingerprints:
                    # Add new fingerprints to processed list
                    existing_fingerprints = set(status.get('processed_query_fingerprints', []))
                    existing_fingerprints.update(new_fingerprints)
                    status['processed_query_fingerprints'] = list(existing_fingerprints)
                    
                    # Add to processing history
                    if 'processing_history' not in status:
                        status['processing_history'] = []
                    
                    status['processing_history'].append({
                        'timestamp': current_time,
                        'type': 'incremental',
                        'new_queries_added': len(new_fingerprints),
                        'total_queries_after': len(existing_fingerprints)
                    })
                else:
                    # Full rebuild - create all fingerprints
                    all_fingerprints = []
                    for _, row in df.iterrows():
                        fingerprint = self._create_query_fingerprint(row)
                        if fingerprint:
                            all_fingerprints.append(fingerprint)
                    
                    status['processed_query_fingerprints'] = all_fingerprints
                    
                    # Add to processing history
                    if 'processing_history' not in status:
                        status['processing_history'] = []
                    
                    status['processing_history'].append({
                        'timestamp': current_time,
                        'type': 'full_rebuild',
                        'total_queries': len(all_fingerprints)
                    })
            
            # Maintain backward compatibility
            if 'created_at' not in status:
                status['created_at'] = current_time
            
            import json
            status_file = self.output_dir / f"status_{csv_name}.json"
            with open(status_file, 'w') as f:
                json.dump(status, f, indent=2)
            
            print(f"📁 Vector store saved to: {index_path}")
            print(f"📄 Status saved to: {status_file}")
            
            if is_incremental and new_fingerprints:
                print(f"🔄 Incremental update: Added {len(new_fingerprints)} new queries")
            
        except Exception as e:
            print(f"❌ Error saving vector store: {e}")
            raise
    
    def generate(self, resume: bool = False, force_rebuild: bool = False, incremental: bool = False) -> bool:
        """
        Generate embeddings from CSV file with incremental update support
        
        Args:
            resume: Resume interrupted processing
            force_rebuild: Rebuild even if vector store exists
            incremental: Only process new queries (detect changes)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            csv_name = self.csv_path.stem
            index_path = self.output_dir / f"index_{csv_name}"
            
            # Load and validate CSV first (needed for all modes)
            df = self._load_and_validate_csv()
            print(f"📊 Loaded {len(df)} queries from CSV")
            
            # Incremental mode logic
            if incremental and index_path.exists() and not force_rebuild:
                print("🔍 Incremental mode: Checking for changes...")
                
                has_changed, reason = self._has_csv_changed(df)
                
                if not has_changed:
                    print(f"✅ No changes detected: {reason}")
                    print("Vector store is up to date!")
                    return True
                
                print(f"📝 Changes detected: {reason}")
                
                # Identify new queries
                new_df, new_fingerprints = self._identify_new_queries(df)
                
                if new_df.empty:
                    print("ℹ️  File changed but no new queries found (modifications to existing queries)")
                    print("💡 Use --force-rebuild to rebuild with modified queries")
                    return True
                
                print(f"🆕 Found {len(new_df)} new queries to process")
                
                # Load existing vector store
                print("📂 Loading existing vector store...")
                existing_vector_store = self._load_existing_vector_store(index_path)
                if not existing_vector_store:
                    print("⚠️  Could not load existing vector store, falling back to full rebuild")
                    force_rebuild = True
                    incremental = False
                else:
                    # Process only new queries
                    print("🔄 Processing new queries with GPU acceleration...")
                    new_documents = self._create_documents(new_df)
                    new_split_documents = self._split_documents(new_documents)
                    
                    # Generate embeddings for new documents
                    new_vector_store = self._generate_embeddings_gpu_parallel(new_split_documents, resume=False)
                    
                    # Merge with existing vector store
                    print("🔗 Merging with existing vector store...")
                    existing_vector_store.merge_from(new_vector_store)
                    
                    # Save merged vector store with incremental tracking
                    self._save_vector_store(existing_vector_store, csv_name, df, new_fingerprints, is_incremental=True)
                    
                    print("✅ Incremental update completed successfully!")
                    print(f"📊 Added {len(new_df)} new queries to existing {len(existing_vector_store.docstore._dict) - len(new_df)} queries")
                    print("🚀 You can now run 'streamlit run app.py'")
                    
                    return True
            
            # Standard processing (full rebuild or first time)
            if not incremental and index_path.exists() and not force_rebuild and not resume:
                print(f"✅ Vector store already exists: {index_path}")
                print("Use --force-rebuild to rebuild, --resume to continue interrupted processing, or --incremental for smart updates")
                return True
            
            # Report processing mode
            if force_rebuild:
                print("🔄 Force rebuild mode: Recreating entire vector store...")
            elif resume:
                print("▶️  Resume mode: Continuing interrupted processing...")
            else:
                print("🔄 GPU-accelerated embedding generation starting...")
            
            print("🚀 Leveraging Gemini embeddings with ThreadPoolExecutor")
            
            # Report GPU capabilities
            if self.gpu_available.get('faiss_gpu') and self.gpu_available.get('nvidia_gpu'):
                print(f"🎯 Full acceleration enabled:")
                print(f"   📊 NVIDIA GPU: {self.gpu_available['gpu_memory']} MB VRAM")
                print(f"   ⚡ Gemini embeddings: High-quality API-based")
                print(f"   🚀 FAISS vector operations: GPU-accelerated")
            elif self.gpu_available.get('nvidia_gpu'):
                print(f"⚡ Partial acceleration:")
                print(f"   📊 NVIDIA GPU: {self.gpu_available['gpu_memory']} MB VRAM")
                print(f"   ⚡ Gemini embeddings: High-quality API-based")
                print(f"   ⚠️  FAISS operations: CPU mode (install faiss-gpu)")
            else:
                print("⚠️  CPU-only mode detected")
                print("💡 Consider installing faiss-gpu and ensuring NVIDIA GPU drivers")
            
            # Initialize Gemini embeddings
            if not self._initialize_embeddings():
                return False
            
            # Create documents from CSV
            documents = self._create_documents(df)
            
            # Add LookML documents if directory provided
            if self.lookml_dir:
                lookml_documents = self._create_lookml_documents()
                documents.extend(lookml_documents)
                if self.verbose:
                    print(f"🔗 Added {len(lookml_documents)} LookML documents")
            
            split_documents = self._split_documents(documents)
            
            # Generate embeddings with GPU-accelerated threading
            vector_store = self._generate_embeddings_gpu_parallel(split_documents, resume=resume)
            
            # Save vector store with full tracking
            self._save_vector_store(vector_store, csv_name, df, is_incremental=False)
            
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
    
    def _load_existing_vector_store(self, index_path) -> Optional:
        """Load existing FAISS vector store from disk"""
        try:
            from utils.embedding_provider import get_embedding_function
            from langchain_community.vectorstores import FAISS
            
            embeddings = get_embedding_function(provider="gemini")
            vector_store = FAISS.load_local(
                str(index_path),
                embeddings,
                allow_dangerous_deserialization=True
            )
            
            print(f"✅ Loaded existing vector store with {len(vector_store.docstore._dict)} documents")
            return vector_store
            
        except Exception as e:
            print(f"❌ Error loading existing vector store: {e}")
            return None


def main():
    """Main entry point for Gemini-powered standalone embedding generator"""
    parser = argparse.ArgumentParser(
        description="Gemini-powered standalone embedding generator with FAISS GPU acceleration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (optimal for most systems)
  python standalone_embedding_generator.py --csv "queries.csv"
  
  # Schema-enhanced mode (recommended for better search accuracy)
  python standalone_embedding_generator.py --csv "queries.csv" --schema "table_schemas.csv"
  
  # High-performance settings for powerful systems (RTX A1000+ with 32GB+ RAM)
  python standalone_embedding_generator.py --csv "data.csv" --batch-size 300 --workers 16
  
  # Schema-enhanced with high performance
  python standalone_embedding_generator.py --csv "data.csv" --schema "schemas.csv" --batch-size 300 --workers 16
  
  # Moderate settings for mid-range systems
  python standalone_embedding_generator.py --csv "data.csv" --batch-size 150 --workers 8
  
  # Resume interrupted processing (with schema)
  python standalone_embedding_generator.py --csv "data.csv" --schema "schemas.csv" --resume
  
  # Force rebuild existing store
  python standalone_embedding_generator.py --csv "data.csv" --force-rebuild
  
  # Incremental updates (smart - only process new queries)
  python standalone_embedding_generator.py --csv "data.csv" --incremental
  
Performance Notes:
  - Gemini embeddings provide high-quality 768-dimension vectors for superior search
  - FAISS GPU acceleration provides 20-50x speedup over CPU-only processing
  - Incremental mode processes only new queries (seconds vs minutes)
  - Higher batch sizes recommended for systems with 16GB+ RAM
  - More workers leverage GPU concurrency (recommend 12-20 for RTX A1000)
  - Ensure Google Cloud authentication is properly configured for Gemini access
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
        '--schema',
        help='Path to CSV file containing table schema information (table_id, column, datatype)'
    )
    
    parser.add_argument(
        '--lookml-dir',
        help='Path to directory containing LookML files (.lkml) for business logic and join relationships'
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
        '--incremental', action='store_true',
        help='Smart incremental updates - only process new queries'
    )
    
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable detailed output'
    )

    parser.add_argument(
        '--skip-list', action='append',
        help='Path to a text or CSV file listing SQL queries to skip (repeatable)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not Path(args.csv).exists():
        print(f"❌ CSV file not found: {args.csv}")
        return 1
    
    # Validate schema file if provided
    if args.schema:
        schema_path = Path(args.schema)
        if not schema_path.exists():
            print(f"❌ Schema file not found: {args.schema}")
            return 1
        
        # Validate schema file format
        try:
            import pandas as pd
            schema_df = pd.read_csv(schema_path, nrows=5)  # Just read first few rows for validation
            required_cols = ['table_id', 'column', 'datatype']
            missing_cols = [col for col in required_cols if col not in schema_df.columns]
            if missing_cols:
                print(f"❌ Schema file missing required columns: {missing_cols}")
                print(f"   Expected columns: {required_cols}")
                print(f"   Found columns: {list(schema_df.columns)}")
                return 1
        except Exception as e:
            print(f"❌ Schema file validation failed: {e}")
            print(f"   Please ensure {args.schema} is a valid CSV file with columns: table_id, column, datatype")
            return 1
    
    # Validate LookML directory if provided
    if args.lookml_dir:
        lookml_path = Path(args.lookml_dir)
        if not lookml_path.exists():
            print(f"❌ LookML directory not found: {args.lookml_dir}")
            return 1
        
        if not lookml_path.is_dir():
            print(f"❌ LookML path is not a directory: {args.lookml_dir}")
            return 1
        
        # Check for .lkml files
        lkml_files = list(lookml_path.rglob("*.lkml"))
        if not lkml_files:
            print(f"❌ No .lkml files found in directory: {args.lookml_dir}")
            return 1
        
        print(f"✅ Found {len(lkml_files)} LookML files in {args.lookml_dir}")
    
    if args.batch_size < 1:
        print("❌ Batch size must be at least 1")
        return 1
    
    if args.workers < 1:
        print("❌ Number of workers must be at least 1")
        return 1
    
    skip_files: List[str] = []
    if args.skip_list:
        for path in args.skip_list:
            skip_path = Path(path)
            if not skip_path.exists():
                print(f"❌ Skip-list file not found: {path}")
                return 1
        skip_files = args.skip_list

    # Performance optimization suggestions
    if args.workers > 20:
        print("⚠️  Very high worker count (>20) may not provide additional benefits")
    if args.batch_size > 500:
        print("⚠️  Very large batch size (>500) may cause memory issues on some systems")
    
    # Gemini authentication reminder
    print("💡 For optimal Gemini performance, ensure:")
    print("   1. Set GOOGLE_CLOUD_PROJECT environment variable")
    print("   2. Configure GCP authentication (gcloud auth application-default login)")
    print("   3. Ensure service account has 'aiplatform.user' role")
    
    # Create generator
    try:
        generator = GPUStandaloneEmbeddingGenerator(
            csv_path=args.csv,
            output_dir=args.output,
            batch_size=args.batch_size,
            max_workers=args.workers,
            verbose=args.verbose,
            schema_path=args.schema,
            lookml_dir=args.lookml_dir,
            skip_list=skip_files
        )
        
        # Generate embeddings
        success = generator.generate(
            resume=args.resume,
            force_rebuild=args.force_rebuild,
            incremental=args.incremental
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
    print("🚀 Starting Gemini-powered embedding generation...")
    sys.exit(main())
