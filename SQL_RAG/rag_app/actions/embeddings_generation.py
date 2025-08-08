"""
Vector Store Builder Module

This module handles the creation and management of FAISS vector stores for RAG applications.
It can process both directory-based SQL files and CSV files containing SQL queries.
"""

import os
import pathlib
import csv
import re
import hashlib
import pandas as pd
from typing import List, Optional, Union
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

def _create_embedding_batch(batch_docs: List[Document]) -> List[Document]:
    """Process a batch of documents for embedding creation."""
    # This function will be called in parallel for each batch
    return batch_docs

# Default paths - can be overridden by function parameters
DEFAULT_DATA_DIR = pathlib.Path("~/Desktop/Test_SQL_Queries").expanduser().resolve()
DEFAULT_INDEX_DIR = pathlib.Path(__file__).resolve().parent / "faiss_indices"

# Regex pattern for virtual environment detection
ENV_PATTERN = re.compile(r'.*(venv|env).*', re.IGNORECASE)


def _load_source_files(source_directory: pathlib.Path = None) -> List[Document]:
    """Walk the specified directory and load .sql and .py files as Documents.
    
    Enhanced version that:
    - Recursively walks through nested folder structures
    - Avoids virtual environment and cache directories
    - Provides better logging and file organization
    - Extracts SQL from Python files with enhanced context
    
    Args:
        source_directory: Path to the directory containing SQL files. 
                         Defaults to DEFAULT_DATA_DIR if not specified.
    """
    if source_directory is None:
        source_directory = DEFAULT_DATA_DIR
    
    # Convert to Path object if string is passed
    if isinstance(source_directory, str):
        source_directory = pathlib.Path(source_directory).expanduser().resolve()
    
    if not source_directory.exists():
        raise ValueError(f"Source directory does not exist: {source_directory}")
    
    if not source_directory.is_dir():
        raise ValueError(f"Source path is not a directory: {source_directory}")
    
    print(f"Using source directory: {source_directory}")
    docs: List[Document] = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    
    # Directories to avoid (virtual environments, caches, etc.)
    EXCLUDED_DIRS = {
        '.venv', 'venv', 'env', '.env',
        '__pycache__', '.git', '.svn',
        'node_modules', 'dist', 'build',
        'temp_env', 'tmp', '.pytest_cache',
        '.mypy_cache', '.tox', 'coverage'
    }
    
    # Statistics tracking
    stats = {
        'folders_processed': 0,
        'folders_skipped': 0,
        'sql_files_found': 0,
        'py_files_found': 0,
        'total_chunks_created': 0,
        'skipped_files': []
    }
    
    def should_skip_directory(dir_path: pathlib.Path) -> bool:
        """Check if directory should be skipped based on exclusion patterns."""
        dir_name = dir_path.name.lower()
        
        # Check exact matches
        if dir_name in EXCLUDED_DIRS:
            return True
            
        # Check patterns for hidden directories
        if (dir_name.startswith('.') and len(dir_name) > 1 and 
            dir_name not in {'.sql', '.py'}):  # Skip hidden dirs but not file extensions
            return True
            
        # Simple regex for virtual environments - much cleaner than multiple string checks
        if ENV_PATTERN.match(dir_name):
            return True
            
        if dir_name.endswith('_cache'):
            return True
            
        return False
    
    def extract_sql_from_python(file_path: pathlib.Path, text: str) -> List[tuple]:
        """Extract SQL queries from Python files with enhanced context."""
        sql_chunks = []
        lines = text.split('\n')
        
        in_sql_string = False
        current_sql = []
        sql_start_line = 0
        function_context = None
        indent_level = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Track function context
            if stripped.startswith('def ') and '(' in stripped:
                function_context = stripped.split('(')[0].replace('def ', '').strip()
            
            # Look for SQL string indicators
            if (not in_sql_string and 
                ('"""' in line or "'''" in line or 
                 'return """' in line or 'return \'\'\'' in line or
                 '= """' in line or "= '''" in line)):
                in_sql_string = True
                sql_start_line = i
                indent_level = len(line) - len(line.lstrip())
                
                # Extract SQL content from the same line if present
                if '"""' in line:
                    sql_content = line.split('"""', 1)[1] if line.count('"""') == 1 else line.split('"""')[1]
                    if sql_content.strip():
                        current_sql.append(sql_content)
                elif "'''" in line:
                    sql_content = line.split("'''", 1)[1] if line.count("'''") == 1 else line.split("'''")[1]
                    if sql_content.strip():
                        current_sql.append(sql_content)
                continue
            
            if in_sql_string:
                # Check for end of SQL string
                if ('"""' in line and line.count('"""') % 2 == 1) or ("'''" in line and line.count("'''") % 2 == 1):
                    # Extract any SQL before the closing quotes
                    if '"""' in line:
                        sql_content = line.split('"""')[0]
                    else:
                        sql_content = line.split("'''")[0]
                    
                    if sql_content.strip():
                        current_sql.append(sql_content)
                    
                    # Process the collected SQL
                    if current_sql:
                        full_sql = '\n'.join(current_sql)
                        if any(keyword in full_sql.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE']):
                            context_info = f"Python file: {file_path.name}"
                            if function_context:
                                context_info += f" | Function: {function_context}()"
                            
                            sql_chunks.append((full_sql.strip(), context_info, sql_start_line))
                    
                    # Reset for next SQL block
                    in_sql_string = False
                    current_sql = []
                    function_context = None
                else:
                    # Continue collecting SQL lines
                    current_sql.append(line)
        
        return sql_chunks
    
    def process_directory(dir_path: pathlib.Path, depth: int = 0) -> None:
        """Recursively process directory and its subdirectories."""
        # Safety: prevent infinite recursion
        if depth > 20:  # Reasonable max depth
            print(f"Skipping deep directory (depth {depth}): {dir_path.relative_to(source_directory)}")
            return
            
        if should_skip_directory(dir_path):
            stats['folders_skipped'] += 1
            print(f"Skipping excluded directory: {dir_path.relative_to(source_directory)}")
            return
        
        stats['folders_processed'] += 1
        print(f"Processing directory: {dir_path.relative_to(source_directory)}")
        
        # Process files in current directory
        for file_path in dir_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in {".sql", ".py"}:
                try:
                    text = file_path.read_text(encoding="utf-8")
                    relative_path = str(file_path.relative_to(source_directory))
                    
                    if file_path.suffix.lower() == ".sql":
                        stats['sql_files_found'] += 1
                        # Process SQL files directly
                        for i, chunk in enumerate(splitter.split_text(text)):
                            metadata = {
                                "source": relative_path,
                                "chunk": i,
                                "file_type": "direct_sql",
                                "folder_path": str(file_path.parent.relative_to(source_directory))
                            }
                            docs.append(Document(page_content=chunk, metadata=metadata))
                            stats['total_chunks_created'] += 1
                    
                    elif file_path.suffix.lower() == ".py":
                        stats['py_files_found'] += 1
                        # Extract SQL from Python files
                        sql_chunks = extract_sql_from_python(file_path, text)
                        
                        if sql_chunks:
                            for sql_content, context, line_num in sql_chunks:
                                # Add context header to SQL content
                                enhanced_content = f"-- {context}\n-- Line {line_num + 1}\n\n{sql_content}"
                                
                                for i, chunk in enumerate(splitter.split_text(enhanced_content)):
                                    metadata = {
                                        "source": relative_path,
                                        "chunk": i,
                                        "file_type": "python_sql",
                                        "folder_path": str(file_path.parent.relative_to(source_directory)),
                                        "context": context,
                                        "line_number": line_num + 1
                                    }
                                    docs.append(Document(page_content=chunk, metadata=metadata))
                                    stats['total_chunks_created'] += 1
                        else:
                            # Also include Python files without SQL for completeness
                            for i, chunk in enumerate(splitter.split_text(text)):
                                metadata = {
                                    "source": relative_path,
                                    "chunk": i,
                                    "file_type": "python_code",
                                    "folder_path": str(file_path.parent.relative_to(source_directory))
                                }
                                docs.append(Document(page_content=chunk, metadata=metadata))
                                stats['total_chunks_created'] += 1
                    
                except Exception as e:
                    stats['skipped_files'].append(f"{relative_path}: {e}")
                    print(f"Skipping {relative_path} due to read error: {e}")
        
        # Recursively process subdirectories (skip excluded dirs early for performance)
        try:
            for subdir in dir_path.iterdir():
                if subdir.is_dir() and not should_skip_directory(subdir):
                    process_directory(subdir, depth + 1)
        except (PermissionError, OSError) as e:
            print(f"Cannot access subdirectories in {dir_path.relative_to(source_directory)}: {e}")
            stats['skipped_files'].append(f"{dir_path.relative_to(source_directory)}: {e}")
    
    print(f"Starting enhanced file discovery in: {source_directory}")
    process_directory(source_directory)
    
    # Print discovery statistics
    print(f"\n=== File Discovery Summary ===")
    print(f"Folders processed: {stats['folders_processed']}")
    print(f"Folders skipped: {stats['folders_skipped']}")
    print(f"SQL files found: {stats['sql_files_found']}")
    print(f"Python files found: {stats['py_files_found']}")
    print(f"Total chunks created: {stats['total_chunks_created']}")
    
    if stats['skipped_files']:
        print(f"\nSkipped files ({len(stats['skipped_files'])}):")
        for skipped in stats['skipped_files'][:5]:  # Show first 5
            print(f"  - {skipped}")
        if len(stats['skipped_files']) > 5:
            print(f"  ... and {len(stats['skipped_files']) - 5} more")
    
    print(f"\nTotal documents created: {len(docs)}")
    return docs


def _load_queries_from_dataframe(df: pd.DataFrame) -> List[Document]:
    """Load SQL queries from a DataFrame with a 'query' column.
    
    Expected DataFrame structure:
    - Required column: 'query' - contains the SQL query text
    - Optional columns: Any additional columns will be included as metadata
    
    Args:
        df: DataFrame containing queries
        
    Returns:
        List of Document objects with query content and metadata
    """
    # Validate required column
    if 'query' not in df.columns:
        raise ValueError(f"DataFrame must contain a 'query' column. Found columns: {df.columns.tolist()}")
    
    docs: List[Document] = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    
    stats = {
        'total': 0,
        'empty': 0,
        'has_description': 0,
    }
    
    # Process each row
    for idx, row in df.iterrows():
        stats['total'] += 1
        
        # Skip empty queries
        query = row.get('query', '')
        if not query or pd.isna(query):
            stats['empty'] += 1
            continue
        
        # Convert query to string if it's not already
        if not isinstance(query, str):
            query = str(query)
        
        # Extract metadata from all other columns
        metadata = {col: str(val) if pd.notna(val) else '' for col, val in row.items() if col != 'query'}
        
        # Track if we have a description
        if metadata.get('description'):
            stats['has_description'] += 1
        
        # Create document with source ID and add to list
        metadata['source'] = f"Query {idx + 1}"
        metadata['chunk'] = 1  # Only one chunk per query in this mode
        
        # Create document with metadata
        doc = Document(page_content=query, metadata=metadata)
        
        # Split into chunks if too large
        if len(query) > 1000:
            chunks = splitter.split_documents([doc])
            for i, chunk in enumerate(chunks):
                chunk.metadata['chunk'] = i + 1
                docs.append(chunk)
        else:
            docs.append(doc)
    
    print(f"Processed {stats['total']} rows, {stats['empty']} empty queries skipped")
    print(f"Found {stats['has_description']} queries with descriptions")
    
    return docs

def _load_queries_from_csv(csv_path: Union[str, pathlib.Path]) -> List[Document]:
    """Load SQL queries from a CSV file with a 'query' column.
    
    Expected CSV structure:
    - Required column: 'query' - contains the SQL query text
    - Optional columns: Any additional columns will be included as metadata
    
    Args:
        csv_path: Path to the CSV file containing queries
        
    Returns:
        List of Document objects with query content and metadata
    """
    if isinstance(csv_path, str):
        csv_path = pathlib.Path(csv_path).expanduser().resolve()
    
    if not csv_path.exists():
        raise ValueError(f"CSV file does not exist: {csv_path}")
    
    if not csv_path.is_file():
        raise ValueError(f"CSV path is not a file: {csv_path}")
    
    print(f"Loading queries from CSV: {csv_path}")
    
    docs: List[Document] = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            delimiter=','
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            # Validate required column
            if 'query' not in reader.fieldnames:
                raise ValueError(f"CSV must contain a 'query' column. Found columns: {reader.fieldnames}")
            
            stats = {
                'queries_processed': 0,
                'chunks_created': 0,
                'empty_queries_skipped': 0,
                'error_queries': []
            }
            
            for row_idx, row in enumerate(reader, start=1):
                query_text = row.get('query', '').strip()
                
                if not query_text:
                    stats['empty_queries_skipped'] += 1
                    continue
                
                try:
                    # Create base metadata from CSV row
                    metadata = {
                        'source': f"csv_row_{row_idx}",
                        'file_type': 'csv_query',
                        'csv_file': str(csv_path.name),
                        'row_number': row_idx
                    }
                    
                    # Add all other CSV columns as metadata (except 'query')
                    for key, value in row.items():
                        if key != 'query' and value:  # Skip empty values
                            metadata[key] = value
                    
                    # Split query into chunks if needed
                    chunks = splitter.split_text(query_text)
                    
                    for chunk_idx, chunk in enumerate(chunks):
                        chunk_metadata = metadata.copy()
                        chunk_metadata['chunk'] = chunk_idx
                        
                        # Add query context if this is part of a larger query
                        if len(chunks) > 1:
                            chunk_metadata['total_chunks'] = len(chunks)
                        
                        docs.append(Document(page_content=chunk, metadata=chunk_metadata))
                        stats['chunks_created'] += 1
                    
                    stats['queries_processed'] += 1
                    
                except Exception as e:
                    stats['error_queries'].append(f"Row {row_idx}: {e}")
                    print(f"Error processing row {row_idx}: {e}")
            
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")
    
    # Print statistics
    print(f"\n=== CSV Loading Summary ===")
    print(f"Queries processed: {stats['queries_processed']}")
    print(f"Empty queries skipped: {stats['empty_queries_skipped']}")
    print(f"Total chunks created: {stats['chunks_created']}")
    
    if stats['error_queries']:
        print(f"\nErrors encountered ({len(stats['error_queries'])}):") 
        for error in stats['error_queries'][:5]:  # Show first 5
            print(f"  - {error}")
        if len(stats['error_queries']) > 5:
            print(f"  ... and {len(stats['error_queries']) - 5} more")
    
    print(f"\nTotal documents created: {len(docs)}")
    return docs

def _create_embeddings_parallel(documents: List[Document], embeddings_model, batch_size: int = 100, max_workers: int = 8) -> FAISS:
    """Create FAISS vector store using parallel batch processing."""
    
    # Split documents into batches
    batches = [documents[i:i + batch_size] for i in range(0, len(documents), batch_size)]
    print(f"📦 Split {len(documents)} documents into {len(batches)} batches of ~{batch_size} each")
    
    start_time = time.time()
    
    # Process batches in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        print(f"🚀 Processing {len(batches)} batches in parallel with {max_workers} workers...")
        
        # Map the batch processing function over all batches
        processed_batches = list(executor.map(_create_embedding_batch, batches))
    
    # Flatten the processed batches back into a single list
    all_documents = [doc for batch in processed_batches for doc in batch]
    
    parallel_time = time.time() - start_time
    print(f"⚡ Parallel processing completed in {parallel_time:.2f}s")
    
    # Create the actual FAISS vector store (this part is still sequential)
    print("🔧 Building FAISS index from processed documents...")
    embed_start = time.time()
    vector_store = FAISS.from_documents(all_documents, embeddings_model)
    embed_time = time.time() - embed_start
    
    total_time = time.time() - start_time
    print(f"📈 Embedding creation: {embed_time:.2f}s | Total time: {total_time:.2f}s")
    
    return vector_store

def build_or_load_vector_store(
    source_directory: pathlib.Path = None, 
    index_directory: pathlib.Path = None,
    csv_path: Optional[Union[str, pathlib.Path]] = None,
    dataframe: Optional[pd.DataFrame] = None,
    force_rebuild: bool = False,
    batch_size: int = 50,
    max_workers: int = 4
) -> FAISS:
    """
    Build a FAISS vector store using the recommended save_local/load_local methods,
    or load it from a local directory if it already exists.
    
    For CSV mode, automatically detects changes and rebuilds/updates the index as needed.
    For DataFrame mode, directly uses the provided DataFrame without file I/O.
    
    Args:
        source_directory: Path to directory containing SQL files. Defaults to DEFAULT_DATA_DIR.
        index_directory: Path to directory for storing FAISS index. Defaults to DEFAULT_INDEX_DIR.
        csv_path: Optional path to CSV file with 'query' column. If provided, loads from CSV instead of directory.
        dataframe: Optional DataFrame with 'query' column. If provided, uses this DataFrame directly.
        force_rebuild: If True, rebuild index regardless of change detection.
        
    Returns:
        FAISS vector store ready for similarity search
        
    Raises:
        ValueError: If no source documents are found or data source is invalid
        Exception: If vector store creation fails
    """
    if source_directory is None:
        source_directory = DEFAULT_DATA_DIR
    if index_directory is None:
        index_directory = DEFAULT_INDEX_DIR
    
    # Convert to Path objects if strings are passed
    if isinstance(source_directory, str):
        source_directory = pathlib.Path(source_directory).expanduser().resolve()
    if isinstance(index_directory, str):
        index_directory = pathlib.Path(index_directory).expanduser().resolve()
    if isinstance(csv_path, str) and csv_path:
        csv_path = pathlib.Path(csv_path).expanduser().resolve()
    
    # Create unique index path based on source
    if dataframe is not None:
        # DataFrame mode - use a consistent identifier
        source_identifier = "bigquery_data"
        print(f"DataFrame mode: Using provided DataFrame with {len(dataframe)} rows")
    elif csv_path:
        # CSV mode - use CSV filename for index path
        source_identifier = f"csv_{csv_path.stem}"
        print(f"CSV mode: Using CSV file {csv_path}")
    else:
        # Directory mode - use directory name for index path
        source_name = source_directory.name
        path_parts = source_directory.parts[-2:] if len(source_directory.parts) >= 2 else source_directory.parts
        source_identifier = "_".join(path_parts).replace(" ", "_")
        print(f"Directory mode: Using directory {source_directory}")
    
    index_path = index_directory / f"index_{source_identifier}"
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    
    # Try to load existing index unless force_rebuild is True
    if not force_rebuild and index_path.exists() and index_path.is_dir():
        try:
            print(f"Loading existing vector store from {index_path}")
            vector_store = FAISS.load_local(
                str(index_path),
                embeddings,
                allow_dangerous_deserialization=True
            )
            
            # If we have new data to add (dataframe provided)
            if dataframe is not None:
                # Load new documents from dataframe
                new_docs = _load_queries_from_dataframe(dataframe)
                
                # Create a hash of each document's content to identify duplicates
                existing_hashes = set()
                new_docs_filtered = []
                
                # Try to extract existing document hashes
                try:
                    if hasattr(vector_store, 'docstore') and hasattr(vector_store.docstore, '_dict'):
                        for doc_id, doc in vector_store.docstore._dict.items():
                            if hasattr(doc, 'page_content'):
                                # Generate hash of content to identify duplicates
                                content_hash = hashlib.md5(doc.page_content.encode('utf-8')).hexdigest()
                                existing_hashes.add(content_hash)
                except Exception as e:
                    print(f"Warning: Could not extract existing document hashes: {e}")
                
                # Filter out documents that already exist based on content hash
                for doc in new_docs:
                    content_hash = hashlib.md5(doc.page_content.encode('utf-8')).hexdigest()
                    if content_hash not in existing_hashes:
                        new_docs_filtered.append(doc)
                        existing_hashes.add(content_hash)  # Add to set to avoid duplicates within new batch
                
                if new_docs_filtered:
                    print(f"Adding {len(new_docs_filtered)} new documents to vector store")
                    # Extract texts and metadatas for add_texts method
                    texts = [doc.page_content for doc in new_docs_filtered]
                    metadatas = [doc.metadata for doc in new_docs_filtered]
                    vector_store.add_texts(texts=texts, metadatas=metadatas)
                    
                    # Save updated vector store
                    vector_store.save_local(str(index_path))
                    print(f"Updated vector store saved to {index_path}")
                else:
                    print("No new documents to add")
                
                return vector_store
            else:
                print("Using existing vector store without updates")
                return vector_store
                
        except Exception as e:
            print(f"Error loading existing vector store: {e}")
            print("Falling back to building new vector store")

    print("Building new FAISS index...")
    
    if dataframe is not None:
        documents = _load_queries_from_dataframe(dataframe)
        if not documents:
            raise ValueError(
                "No queries found in DataFrame. "
                "Ensure the DataFrame contains a 'query' column with SQL queries."
            )
        print(f"📊 Loaded {len(documents)} queries from DataFrame")
        print(f"🔧 Creating vector embeddings for {len(documents)} queries...")
    elif csv_path:
        documents = _load_queries_from_csv(csv_path)
        if not documents:
            raise ValueError(
                f"No queries found in CSV file '{csv_path}'. "
                "Ensure the CSV contains a 'query' column with SQL queries."
            )
        print(f"📊 Loaded {len(documents)} queries from {csv_path.name}")
        print(f"🔧 Creating vector embeddings for {len(documents)} queries...")
    else:
        documents = _load_source_files(source_directory)
        if not documents:
            raise ValueError(
                f"No source documents found. Ensure the directory '{source_directory}' "
                "contains .sql or .py files."
            )
        
    if len(documents) > batch_size:
        print(f"🔧 Creating vector embeddings for {len(documents)} documents using {max_workers} parallel workers...")
        vector_store = _create_embeddings_parallel(documents, embeddings, batch_size, max_workers)
    else:
        print(f"🔧 Creating vector embeddings for {len(documents)} documents (standard processing)...")
        vector_store = FAISS.from_documents(documents, embeddings)
    
    # Save the vector store for future incremental updates
    if index_path:
        os.makedirs(index_path.parent, exist_ok=True)
        vector_store.save_local(str(index_path))
        print(f"Vector store saved to {index_path}")
    
    print(f"✅ Vector embeddings created successfully for {len(documents)} documents")
    
    return vector_store

    # Ensure index directory exists
    index_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Persist index locally for future runs using the recommended method
    print(f"💾 Saving FAISS index to {index_path}")
    vector_store.save_local(str(index_path))
    print(f"✅ Vector index saved successfully")
    
    return vector_store

if __name__ == "__main__":
    """
    Test the vector store builder with the existing test_queries.csv file.
    
    Usage:
        python embeddings_generation.py
        
    This will use the test_queries.csv file in the same directory and build a vector store from it.
    """
    import sys
    
    # Use the existing test_queries.csv file in the same directory
    current_dir = pathlib.Path(__file__).resolve().parent.parent.parent  # Go up one level from actions/
    test_csv_path = current_dir / "sample_queries.csv"
    
    # Check if test_queries.csv exists
    if not test_csv_path.exists():
        print("=" * 60)
        print("ERROR: test_queries.csv file not found")
        print("=" * 60)
        print(f"Expected location: {test_csv_path}")
        print("\nPlease ensure test_queries.csv exists in the directory above this script.")
        print("The CSV should have a 'query' column containing SQL queries.")
        
        # Also check current directory as fallback
        current_dir_csv = current_dir / "actions" / "test_queries.csv"
        if current_dir_csv.exists():
            print(f"\nFound CSV in actions directory: {current_dir_csv}")
            test_csv_path = current_dir_csv
        else:
            sys.exit(1)
    
    try:
        print("=" * 60)
        print("TESTING VECTOR STORE BUILDER")
        print("=" * 60)
        
        print(f"\nUsing existing CSV file: {test_csv_path}")
        
        # Show a preview of the CSV content
        print("\nCSV Preview (first 3 lines):")
        print("-" * 40)
        try:
            with open(test_csv_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines[:3]):
                    # Truncate very long lines for readability
                    display_line = line.rstrip()
                    if len(display_line) > 100:
                        display_line = display_line[:100] + "..."
                    print(f"{i+1}: {display_line}")
                if len(lines) > 3:
                    print(f"... and {len(lines) - 3} more lines")
        except Exception as e:
            print(f"Could not preview CSV: {e}")
        
        print("\n" + "=" * 60)
        print("BUILDING VECTOR STORE FROM CSV")
        print("=" * 60)
        
        # Build vector store
        start_time = time.time()
        vector_store = build_or_load_vector_store(
            csv_path=test_csv_path,
            force_rebuild=True,
            batch_size=100,      # Smaller batches for testing
            max_workers=9       # Conservative for testing
        )
        total_time = time.time() - start_time
        
        print(f"🎉 Total processing time: {total_time:.2f} seconds")
        
        print("\n" + "=" * 60)
        print("TESTING SIMILARITY SEARCH")
        print("=" * 60)
        
        # Test similarity search with queries relevant to your BigQuery/Walmart data
        test_queries = [
            "How to join customer data with transactions?",
            "Show me panelist purchase behavior", 
            "How to calculate customer metrics over time periods?",
            "Find customers who bought specific UPC codes",
            "Get transaction data from BigQuery tables",
            "How to filter by date ranges and group results?"
        ]
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            print("-" * 40)
            try:
                results = vector_store.similarity_search(query, k=2)
                if results:
                    for i, doc in enumerate(results, 1):
                        # Show more relevant preview for SQL content
                        content_preview = doc.page_content[:200].replace('\n', ' ').replace('  ', ' ')
                        print(f"Result {i}:")
                        print(f"  Content: {content_preview}...")
                        print(f"  Source: {doc.metadata.get('source', 'Unknown')}")
                        
                        # Show additional metadata if available
                        metadata_keys = [k for k in doc.metadata.keys() if k not in ['source', 'chunk']]
                        if metadata_keys:
                            metadata_info = ", ".join([f"{k}: {doc.metadata[k]}" for k in metadata_keys[:2]])
                            print(f"  Metadata: {metadata_info}")
                else:
                    print("  No results found")
            except Exception as e:
                print(f"  Error during search: {e}")
        
        print("\n" + "=" * 60)
        print("TESTING VECTOR STORE PERSISTENCE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def process_initial_batch(sql_files_dir: Optional[Union[str, pathlib.Path]] = None,
                         csv_file_path: Optional[Union[str, pathlib.Path]] = None,
                         index_dir: Optional[Union[str, pathlib.Path]] = None,
                         batch_size: int = 100) -> FAISS:
    """
    Process the initial batch of SQL files or CSV records to quickly build a starter vector store.
    
    Args:
        sql_files_dir: Directory containing SQL files (optional)
        csv_file_path: Path to CSV file containing SQL queries (optional)
        index_dir: Directory to save the FAISS index
        batch_size: Number of documents to process in the initial batch (default: 100)
        
    Returns:
        FAISS vector store with initial batch of documents embedded
    """
    # Set default paths if not provided
    if sql_files_dir is None and csv_file_path is None:
        sql_files_dir = DEFAULT_DATA_DIR
    
    if index_dir is None:
        index_dir = DEFAULT_INDEX_DIR
        
    # Ensure the index directory exists
    os.makedirs(index_dir, exist_ok=True)
    
    # Generate a timestamp for versioning
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create embeddings instance
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    
    # Load documents
    documents = []
    remaining_documents = []
    
    if sql_files_dir:
        all_docs = _load_source_files(sql_files_dir)
        documents = all_docs[:batch_size]
        remaining_documents = all_docs[batch_size:]
    elif csv_file_path:
        all_docs = _load_queries_from_csv(csv_file_path)
        documents = all_docs[:batch_size]
        remaining_documents = all_docs[batch_size:]
        
    if not documents:
        print("No documents found to process")
        return None
    
    print(f"Processing initial batch of {len(documents)} documents...")
    
    # Create vector store with initial batch
    vector_store = FAISS.from_documents(documents, embeddings)
    
    # Save the initial vector store
    index_path = os.path.join(index_dir, f"sql_faiss_index_initial_{timestamp}")
    vector_store.save_local(index_path)
    
    print(f"✅ Initial vector store created with {len(documents)} documents and saved to {index_path}")
    
    return vector_store, remaining_documents


def process_remaining_in_background(vector_store: FAISS, 
                                   remaining_documents: List[Document],
                                   index_dir: Optional[Union[str, pathlib.Path]] = None,
                                   max_workers: int = 4,
                                   batch_size: int = 25,
                                   status_file_path: Optional[str] = None):
    """
    Process the remaining documents in background using ThreadPoolExecutor.
    
    Args:
        vector_store: The initial FAISS vector store to add documents to
        remaining_documents: List of remaining documents to process
        index_dir: Directory to save the updated FAISS index
        max_workers: Maximum number of worker threads to use
        batch_size: Size of document batches to process in each thread
        status_file_path: Optional path to the status file for progress tracking
    """
    # Initialize status tracker if path is provided
    status_tracker = None
    if status_file_path:
        from .background_status import BackgroundProcessingStatus
        status_tracker = BackgroundProcessingStatus(status_file_path)
    if not remaining_documents:
        print("No remaining documents to process")
        return
        
    if index_dir is None:
        index_dir = DEFAULT_INDEX_DIR
    
    # Ensure the index directory exists
    os.makedirs(index_dir, exist_ok=True)
    
    # Generate a timestamp for versioning
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    total_docs = len(remaining_documents)
    print(f"Processing remaining {total_docs} documents in background...")
    
    # Create embeddings instance
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    
    # Split documents into batches
    batches = [remaining_documents[i:i+batch_size] for i in range(0, len(remaining_documents), batch_size)]
    
    processed_count = 0
    
    # Process batches in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all batches for processing
        futures = [executor.submit(_create_embedding_batch, batch) for batch in batches]
        
        # Process results as they complete
        for future in futures:
            batch_docs = future.result()
            
            # Add documents to vector store
            vector_store.add_documents(batch_docs)
            
            # Update processed count
            processed_count += len(batch_docs)
            
            # Report progress
            progress = (processed_count / total_docs) * 100
            print(f"Progress: {progress:.2f}% ({processed_count}/{total_docs})")
            
            # Update status if we have a tracker
            if status_tracker:
                status_tracker.update_status(processed_count, total_docs)
            
            # Save intermediate result periodically (every ~25% or at the end)
            if processed_count == total_docs or processed_count % (total_docs // 4) < batch_size:
                index_path = os.path.join(index_dir, f"sql_faiss_index_updated_{timestamp}")
                vector_store.save_local(index_path)
                print(f"Intermediate vector store saved to {index_path}")
    
    # Save the final vector store
    final_index_path = os.path.join(index_dir, f"sql_faiss_index_complete_{timestamp}")
    vector_store.save_local(final_index_path)
    
    print(f"✅ All {total_docs} remaining documents processed and added to vector store")
    print(f"✅ Final vector store saved to {final_index_path}")
    
    return final_index_path


def initialize_vector_store_with_background_processing(
    sql_files_dir: Optional[Union[str, pathlib.Path]] = None,
    csv_file_path: Optional[Union[str, pathlib.Path]] = None,
    index_dir: Optional[Union[str, pathlib.Path]] = None,
    initial_batch_size: int = 100,
    max_workers: int = 4,
    batch_size: int = 25,
    status_file_path: Optional[str] = None
):
    """
    Initialize a vector store with an initial batch of documents and process the rest in background.
    
    Args:
        sql_files_dir: Directory containing SQL files (optional)
        csv_file_path: Path to CSV file containing SQL queries (optional)
        index_dir: Directory to save the FAISS index
        initial_batch_size: Number of documents to process in the initial batch
        max_workers: Maximum number of worker threads for background processing
        batch_size: Size of document batches for background processing
        status_file_path: Optional path to the status file for progress tracking
        
    Returns:
        tuple: (vector_store, background_thread) - The initial vector store and the thread handling background processing
    """
    # Initialize status tracker if path is provided
    if status_file_path:
        from .background_status import BackgroundProcessingStatus
        status_tracker = BackgroundProcessingStatus(status_file_path)
    else:
        status_tracker = None
    # Process the initial batch
    vector_store, remaining_documents = process_initial_batch(
        sql_files_dir=sql_files_dir,
        csv_file_path=csv_file_path,
        index_dir=index_dir,
        batch_size=initial_batch_size
    )
    
    if vector_store is None:
        return None, None
    
    # Start background processing in a separate thread
    import threading
    background_thread = threading.Thread(
        target=process_remaining_in_background,
        args=(vector_store, remaining_documents),
        kwargs={
            'index_dir': index_dir,
            'max_workers': max_workers,
            'batch_size': batch_size,
            'status_file_path': status_file_path
        }
    )
    background_thread.daemon = True  # Make thread exit when main thread exits
    background_thread.start()
    
    print(f"Background processing started in separate thread for {len(remaining_documents)} documents")
    
    return vector_store, background_thread