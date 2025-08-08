import os
import pathlib
import pickle
from typing import List, Optional, Union, Dict
import time
import re
import csv
import json
import hashlib
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from actions import build_or_load_vector_store, _create_embedding_batch,_create_embeddings_parallel,generate_answer_from_context
from actions.progressive_embeddings import build_progressive_vector_store
from dotenv import load_dotenv, find_dotenv
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
#from langchain_ollama import ChatOllama
from google import genai  # Add this import

import streamlit as st

# Load .env regardless of current working directory
#load_dotenv(find_dotenv(), override=False)

# Initialize Google GenAI client
genai_client = genai.Client(
    vertexai=True,
    project="wmt-dv-bq-analytics",
    location="global",
)

class CSVChangeType(Enum):
    """Enum representing different types of CSV changes detected."""
    NO_CHANGE = "no_change"
    ROWS_ADDED = "rows_added"
    ROWS_MODIFIED = "rows_modified"
    SCHEMA_CHANGED = "schema_changed"
    FILE_MISSING = "file_missing"
    FIRST_TIME = "first_time"


@dataclass
class CSVMetadata:
    """Metadata about a CSV file for change detection."""
    file_path: str
    modification_time: float
    row_count: int
    column_hash: str
    last_processed_timestamp: str
    column_names: List[str]
    file_size: int
    
    def to_dict(self) -> dict:
        """Convert metadata to dictionary for JSON serialization."""
        return {
            'file_path': self.file_path,
            'modification_time': self.modification_time,
            'row_count': self.row_count,
            'column_hash': self.column_hash,
            'last_processed_timestamp': self.last_processed_timestamp,
            'column_names': self.column_names,
            'file_size': self.file_size
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CSVMetadata':
        """Create metadata instance from dictionary."""
        return cls(
            file_path=data['file_path'],
            modification_time=data['modification_time'],
            row_count=data['row_count'],
            column_hash=data['column_hash'],
            last_processed_timestamp=data['last_processed_timestamp'],
            column_names=data['column_names'],
            file_size=data['file_size']
        )
    
    def save_to_file(self, metadata_path: pathlib.Path) -> None:
        """Save metadata to JSON file."""
        try:
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save CSV metadata: {e}")
    
    @classmethod
    def load_from_file(cls, metadata_path: pathlib.Path) -> Optional['CSVMetadata']:
        """Load metadata from JSON file."""
        try:
            if not metadata_path.exists():
                return None
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            print(f"Warning: Could not load CSV metadata: {e}")
            return None


# Default paths - can be overridden by function parameters
DEFAULT_DATA_DIR = pathlib.Path("~/Desktop/Test_SQL_Queries").expanduser().resolve()
DEFAULT_INDEX_DIR = pathlib.Path(__file__).resolve().parent / "faiss_indices"
#LLM_MODEL_NAME = "phi3.5:3.8b"  # Ollama Phi3 model
GENAI_MODEL_NAME = "gemini-2.5-pro"  # Google GenAI model

# Regex pattern for virtual environment detection
# ENV_PATTERN = re.compile(r'.*(venv|env).*', re.IGNORECASE)


# def _compute_column_hash(column_names: List[str]) -> str:
#     """Compute a hash of the column names to detect schema changes."""
#     columns_str = "|".join(sorted(column_names))
#     return hashlib.md5(columns_str.encode('utf-8')).hexdigest()


# def get_csv_current_state(csv_path: Union[str, pathlib.Path]) -> CSVMetadata:
#     """Extract current metadata from a CSV file.
    
#     Args:
#         csv_path: Path to the CSV file
        
#     Returns:
#         CSVMetadata object with current file state
        
#     Raises:
#         FileNotFoundError: If CSV file doesn't exist
#         ValueError: If CSV file is invalid or missing required columns
#     """
#     if isinstance(csv_path, str):
#         csv_path = pathlib.Path(csv_path).expanduser().resolve()
    
#     if not csv_path.exists():
#         raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
#     if not csv_path.is_file():
#         raise ValueError(f"Path is not a file: {csv_path}")
    
#     try:
#         # Get file metadata
#         file_stat = csv_path.stat()
#         modification_time = file_stat.st_mtime
#         file_size = file_stat.st_size
        
#         # Read CSV to get structure and row count
#         with open(csv_path, 'r', encoding='utf-8') as csvfile:
#             sample = csvfile.read(1024)
#             csvfile.seek(0)
            
#             # Detect delimiter
#             sniffer = csv.Sniffer()
#             delimiter = sniffer.sniff(sample).delimiter
            
#             reader = csv.DictReader(csvfile, delimiter=delimiter)
#             column_names = list(reader.fieldnames or [])
            
#             if not column_names:
#                 raise ValueError("CSV file appears to be empty or has no headers")
            
#             if 'query' not in column_names:
#                 raise ValueError(f"CSV must contain a 'query' column. Found: {column_names}")
            
#             # Count non-empty rows
#             row_count = 0
#             for row in reader:
#                 if row.get('query', '').strip():  # Only count rows with actual queries
#                     row_count += 1
        
#         # Compute column hash for schema change detection
#         column_hash = _compute_column_hash(column_names)
        
#         # Create timestamp
#         timestamp = datetime.now().isoformat()
        
#         return CSVMetadata(
#             file_path=str(csv_path),
#             modification_time=modification_time,
#             row_count=row_count,
#             column_hash=column_hash,
#             last_processed_timestamp=timestamp,
#             column_names=column_names,
#             file_size=file_size
#         )
        
#     except Exception as e:
#         raise ValueError(f"Error reading CSV file: {e}")


# def compare_csv_states(stored_metadata: Optional[CSVMetadata], 
#                       current_metadata: CSVMetadata) -> CSVChangeType:
#     """Compare stored metadata with current CSV state to detect changes.
    
#     Args:
#         stored_metadata: Previously stored metadata (None if first time)
#         current_metadata: Current CSV file metadata
        
#     Returns:
#         CSVChangeType indicating what type of change was detected
#     """
#     if stored_metadata is None:
#         return CSVChangeType.FIRST_TIME
    
#     # Check if file path changed (shouldn't happen but good to verify)
#     if stored_metadata.file_path != current_metadata.file_path:
#         print(f"Warning: CSV file path changed from {stored_metadata.file_path} to {current_metadata.file_path}")
#         return CSVChangeType.FIRST_TIME
    
#     # Check for schema changes (column structure)
#     if stored_metadata.column_hash != current_metadata.column_hash:
#         print(f"CSV schema changed. Old columns: {stored_metadata.column_names}, New columns: {current_metadata.column_names}")
#         return CSVChangeType.SCHEMA_CHANGED
    
#     # Check for row count changes
#     if stored_metadata.row_count != current_metadata.row_count:
#         if current_metadata.row_count > stored_metadata.row_count:
#             rows_added = current_metadata.row_count - stored_metadata.row_count
#             print(f"CSV has {rows_added} new rows ({stored_metadata.row_count} -> {current_metadata.row_count})")
#             return CSVChangeType.ROWS_ADDED
#         else:
#             rows_removed = stored_metadata.row_count - current_metadata.row_count
#             print(f"CSV has {rows_removed} fewer rows ({stored_metadata.row_count} -> {current_metadata.row_count})")
#             return CSVChangeType.ROWS_MODIFIED
    
#     # Check file modification time
#     if stored_metadata.modification_time != current_metadata.modification_time:
#         print("CSV file modification time changed, but row count is the same - likely row modifications")
#         return CSVChangeType.ROWS_MODIFIED
    
#     # Check file size (additional validation)
#     if stored_metadata.file_size != current_metadata.file_size:
#         print("CSV file size changed, but other metrics unchanged - possible data modifications")
#         return CSVChangeType.ROWS_MODIFIED
    
#     return CSVChangeType.NO_CHANGE


# def detect_csv_changes(csv_path: Union[str, pathlib.Path], 
#                       index_directory: pathlib.Path) -> tuple[CSVChangeType, CSVMetadata, Optional[CSVMetadata]]:
#     """Detect changes in a CSV file by comparing with stored metadata.
    
#     Args:
#         csv_path: Path to the CSV file
#         index_directory: Directory where FAISS index and metadata are stored
        
#     Returns:
#         Tuple of (change_type, current_metadata, stored_metadata)
#     """
#     if isinstance(csv_path, str):
#         csv_path = pathlib.Path(csv_path).expanduser().resolve()
    
#     # Define metadata file path
#     csv_filename = csv_path.stem
#     metadata_path = index_directory / f"index_csv_{csv_filename}" / "csv_metadata.json"
    
#     try:
#         # Get current CSV state
#         current_metadata = get_csv_current_state(csv_path)
        
#         # Load stored metadata if it exists
#         stored_metadata = CSVMetadata.load_from_file(metadata_path)
        
#         # Compare states
#         change_type = compare_csv_states(stored_metadata, current_metadata)
        
#         return change_type, current_metadata, stored_metadata
        
#     except FileNotFoundError:
#         # CSV file was deleted - return file missing status
#         stored_metadata = CSVMetadata.load_from_file(metadata_path)
#         # Create dummy current metadata to represent missing file
#         dummy_metadata = CSVMetadata(
#             file_path=str(csv_path),
#             modification_time=0,
#             row_count=0,
#             column_hash="",
#             last_processed_timestamp="",
#             column_names=[],
#             file_size=0
#         )
#         return CSVChangeType.FILE_MISSING, dummy_metadata, stored_metadata
    
#     except Exception as e:
#         print(f"Error detecting CSV changes: {e}")
#         # Treat errors as requiring rebuild
#         stored_metadata = CSVMetadata.load_from_file(metadata_path)
#         dummy_metadata = CSVMetadata(
#             file_path=str(csv_path),
#             modification_time=0,
#             row_count=0,
#             column_hash="",
#             last_processed_timestamp="",
#             column_names=[],
#             file_size=0
#         )
#         return CSVChangeType.FIRST_TIME, dummy_metadata, stored_metadata


# def _load_source_files(source_directory: pathlib.Path = None) -> List[Document]:
#     """Walk the specified directory and load .sql and .py files as Documents.
    
#     Enhanced version that:
#     - Recursively walks through nested folder structures
#     - Avoids virtual environment and cache directories
#     - Provides better logging and file organization
#     - Extracts SQL from Python files with enhanced context
    
#     Args:
#         source_directory: Path to the directory containing SQL files. 
#                          Defaults to DEFAULT_DATA_DIR if not specified.
#     """
#     if source_directory is None:
#         source_directory = DEFAULT_DATA_DIR
    
#     # Convert to Path object if string is passed
#     if isinstance(source_directory, str):
#         source_directory = pathlib.Path(source_directory).expanduser().resolve()
    
#     if not source_directory.exists():
#         raise ValueError(f"Source directory does not exist: {source_directory}")
    
#     if not source_directory.is_dir():
#         raise ValueError(f"Source path is not a directory: {source_directory}")
    
#     print(f"Using source directory: {source_directory}")
#     docs: List[Document] = []
#     splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    
#     # Directories to avoid (virtual environments, caches, etc.)
#     EXCLUDED_DIRS = {
#         '.venv', 'venv', 'env', '.env',
#         '__pycache__', '.git', '.svn',
#         'node_modules', 'dist', 'build',
#         'temp_env', 'tmp', '.pytest_cache',
#         '.mypy_cache', '.tox', 'coverage'
#     }
    
#     # Statistics tracking
#     stats = {
#         'folders_processed': 0,
#         'folders_skipped': 0,
#         'sql_files_found': 0,
#         'py_files_found': 0,
#         'total_chunks_created': 0,
#         'skipped_files': []
#     }
    
#     def should_skip_directory(dir_path: pathlib.Path) -> bool:
#         """Check if directory should be skipped based on exclusion patterns."""
#         dir_name = dir_path.name.lower()
        
#         # Check exact matches
#         if dir_name in EXCLUDED_DIRS:
#             return True
            
#         # Check patterns for hidden directories
#         if (dir_name.startswith('.') and len(dir_name) > 1 and 
#             dir_name not in {'.sql', '.py'}):  # Skip hidden dirs but not file extensions
#             return True
            
#         # Simple regex for virtual environments - much cleaner than multiple string checks
#         if ENV_PATTERN.match(dir_name):
#             return True
            
#         if dir_name.endswith('_cache'):
#             return True
            
#         return False
    
#     def extract_sql_from_python(file_path: pathlib.Path, text: str) -> List[tuple]:
#         """Extract SQL queries from Python files with enhanced context."""
#         sql_chunks = []
#         lines = text.split('\n')
        
#         in_sql_string = False
#         current_sql = []
#         sql_start_line = 0
#         function_context = None
#         indent_level = 0
        
#         for i, line in enumerate(lines):
#             stripped = line.strip()
            
#             # Track function context
#             if stripped.startswith('def ') and '(' in stripped:
#                 function_context = stripped.split('(')[0].replace('def ', '').strip()
            
#             # Look for SQL string indicators
#             if (not in_sql_string and 
#                 ('"""' in line or "'''" in line or 
#                  'return """' in line or 'return \'\'\'' in line or
#                  '= """' in line or "= '''" in line)):
#                 in_sql_string = True
#                 sql_start_line = i
#                 indent_level = len(line) - len(line.lstrip())
                
#                 # Extract SQL content from the same line if present
#                 if '"""' in line:
#                     sql_content = line.split('"""', 1)[1] if line.count('"""') == 1 else line.split('"""')[1]
#                     if sql_content.strip():
#                         current_sql.append(sql_content)
#                 elif "'''" in line:
#                     sql_content = line.split("'''", 1)[1] if line.count("'''") == 1 else line.split("'''")[1]
#                     if sql_content.strip():
#                         current_sql.append(sql_content)
#                 continue
            
#             if in_sql_string:
#                 # Check for end of SQL string
#                 if ('"""' in line and line.count('"""') % 2 == 1) or ("'''" in line and line.count("'''") % 2 == 1):
#                     # Extract any SQL before the closing quotes
#                     if '"""' in line:
#                         sql_content = line.split('"""')[0]
#                     else:
#                         sql_content = line.split("'''")[0]
                    
#                     if sql_content.strip():
#                         current_sql.append(sql_content)
                    
#                     # Process the collected SQL
#                     if current_sql:
#                         full_sql = '\n'.join(current_sql)
#                         if any(keyword in full_sql.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE']):
#                             context_info = f"Python file: {file_path.name}"
#                             if function_context:
#                                 context_info += f" | Function: {function_context}()"
                            
#                             sql_chunks.append((full_sql.strip(), context_info, sql_start_line))
                    
#                     # Reset for next SQL block
#                     in_sql_string = False
#                     current_sql = []
#                     function_context = None
#                 else:
#                     # Continue collecting SQL lines
#                     current_sql.append(line)
        
#         return sql_chunks
    
#     def process_directory(dir_path: pathlib.Path, depth: int = 0) -> None:
#         """Recursively process directory and its subdirectories."""
#         # Safety: prevent infinite recursion
#         if depth > 20:  # Reasonable max depth
#             print(f"Skipping deep directory (depth {depth}): {dir_path.relative_to(source_directory)}")
#             return
            
#         if should_skip_directory(dir_path):
#             stats['folders_skipped'] += 1
#             print(f"Skipping excluded directory: {dir_path.relative_to(source_directory)}")
#             return
        
#         stats['folders_processed'] += 1
#         print(f"Processing directory: {dir_path.relative_to(source_directory)}")
        
#         # Process files in current directory
#         for file_path in dir_path.iterdir():
#             if file_path.is_file() and file_path.suffix.lower() in {".sql", ".py"}:
#                 try:
#                     text = file_path.read_text(encoding="utf-8")
#                     relative_path = str(file_path.relative_to(source_directory))
                    
#                     if file_path.suffix.lower() == ".sql":
#                         stats['sql_files_found'] += 1
#                         # Process SQL files directly
#                         for i, chunk in enumerate(splitter.split_text(text)):
#                             metadata = {
#                                 "source": relative_path,
#                                 "chunk": i,
#                                 "file_type": "direct_sql",
#                                 "folder_path": str(file_path.parent.relative_to(source_directory))
#                             }
#                             docs.append(Document(page_content=chunk, metadata=metadata))
#                             stats['total_chunks_created'] += 1
                    
#                     elif file_path.suffix.lower() == ".py":
#                         stats['py_files_found'] += 1
#                         # Extract SQL from Python files
#                         sql_chunks = extract_sql_from_python(file_path, text)
                        
#                         if sql_chunks:
#                             for sql_content, context, line_num in sql_chunks:
#                                 # Add context header to SQL content
#                                 enhanced_content = f"-- {context}\n-- Line {line_num + 1}\n\n{sql_content}"
                                
#                                 for i, chunk in enumerate(splitter.split_text(enhanced_content)):
#                                     metadata = {
#                                         "source": relative_path,
#                                         "chunk": i,
#                                         "file_type": "python_sql",
#                                         "folder_path": str(file_path.parent.relative_to(source_directory)),
#                                         "context": context,
#                                         "line_number": line_num + 1
#                                     }
#                                     docs.append(Document(page_content=chunk, metadata=metadata))
#                                     stats['total_chunks_created'] += 1
#                         else:
#                             # Also include Python files without SQL for completeness
#                             for i, chunk in enumerate(splitter.split_text(text)):
#                                 metadata = {
#                                     "source": relative_path,
#                                     "chunk": i,
#                                     "file_type": "python_code",
#                                     "folder_path": str(file_path.parent.relative_to(source_directory))
#                                 }
#                                 docs.append(Document(page_content=chunk, metadata=metadata))
#                                 stats['total_chunks_created'] += 1
                    
#                 except Exception as e:
#                     stats['skipped_files'].append(f"{relative_path}: {e}")
#                     print(f"Skipping {relative_path} due to read error: {e}")
        
#         # Recursively process subdirectories (skip excluded dirs early for performance)
#         try:
#             for subdir in dir_path.iterdir():
#                 if subdir.is_dir() and not should_skip_directory(subdir):
#                     process_directory(subdir, depth + 1)
#         except (PermissionError, OSError) as e:
#             print(f"Cannot access subdirectories in {dir_path.relative_to(source_directory)}: {e}")
#             stats['skipped_files'].append(f"{dir_path.relative_to(source_directory)}: {e}")
    
#     print(f"Starting enhanced file discovery in: {source_directory}")
#     process_directory(source_directory)
    
#     # Print discovery statistics
#     print(f"\n=== File Discovery Summary ===")
#     print(f"Folders processed: {stats['folders_processed']}")
#     print(f"Folders skipped: {stats['folders_skipped']}")
#     print(f"SQL files found: {stats['sql_files_found']}")
#     print(f"Python files found: {stats['py_files_found']}")
#     print(f"Total chunks created: {stats['total_chunks_created']}")
    
#     if stats['skipped_files']:
#         print(f"\nSkipped files ({len(stats['skipped_files'])}):")
#         for skipped in stats['skipped_files'][:5]:  # Show first 5
#             print(f"  - {skipped}")
#         if len(stats['skipped_files']) > 5:
#             print(f"  ... and {len(stats['skipped_files']) - 5} more")
    
#     print(f"\nTotal documents created: {len(docs)}")
#     return docs


# def _load_queries_from_csv(csv_path: Union[str, pathlib.Path]) -> List[Document]:
#     """Load SQL queries from a CSV file with a 'query' column.
    
#     Expected CSV structure:
#     - Required column: 'query' - contains the SQL query text
#     - Optional columns: Any additional columns will be included as metadata
    
#     Args:
#         csv_path: Path to the CSV file containing queries
        
#     Returns:
#         List of Document objects with query content and metadata
#     """
#     if isinstance(csv_path, str):
#         csv_path = pathlib.Path(csv_path).expanduser().resolve()
    
#     if not csv_path.exists():
#         raise ValueError(f"CSV file does not exist: {csv_path}")
    
#     if not csv_path.is_file():
#         raise ValueError(f"CSV path is not a file: {csv_path}")
    
#     print(f"Loading queries from CSV: {csv_path}")
    
#     docs: List[Document] = []
#     splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    
#     try:
#         with open(csv_path, 'r', encoding='utf-8') as csvfile:
#             delimiter=','
#             reader = csv.DictReader(csvfile, delimiter=delimiter)
            
#             # Validate required column
#             if 'query' not in reader.fieldnames:
#                 raise ValueError(f"CSV must contain a 'query' column. Found columns: {reader.fieldnames}")
            
#             stats = {
#                 'queries_processed': 0,
#                 'chunks_created': 0,
#                 'empty_queries_skipped': 0,
#                 'error_queries': []
#             }
            
#             for row_idx, row in enumerate(reader, start=1):
#                 query_text = row.get('query', '').strip()
                
#                 if not query_text:
#                     stats['empty_queries_skipped'] += 1
#                     continue
                
#                 try:
#                     # Create base metadata from CSV row
#                     metadata = {
#                         'source': f"csv_row_{row_idx}",
#                         'file_type': 'csv_query',
#                         'csv_file': str(csv_path.name),
#                         'row_number': row_idx
#                     }
                    
#                     # Add all other CSV columns as metadata (except 'query')
#                     for key, value in row.items():
#                         if key != 'query' and value:  # Skip empty values
#                             metadata[key] = value
                    
#                     # Split query into chunks if needed
#                     chunks = splitter.split_text(query_text)
                    
#                     for chunk_idx, chunk in enumerate(chunks):
#                         chunk_metadata = metadata.copy()
#                         chunk_metadata['chunk'] = chunk_idx
                        
#                         # Add query context if this is part of a larger query
#                         if len(chunks) > 1:
#                             chunk_metadata['total_chunks'] = len(chunks)
                        
#                         docs.append(Document(page_content=chunk, metadata=chunk_metadata))
#                         stats['chunks_created'] += 1
                    
#                     stats['queries_processed'] += 1
                    
#                 except Exception as e:
#                     stats['error_queries'].append(f"Row {row_idx}: {e}")
#                     print(f"Error processing row {row_idx}: {e}")
            
#     except Exception as e:
#         raise ValueError(f"Error reading CSV file: {e}")
    
#     # Print statistics
#     print(f"\n=== CSV Loading Summary ===")
#     print(f"Queries processed: {stats['queries_processed']}")
#     print(f"Empty queries skipped: {stats['empty_queries_skipped']}")
#     print(f"Total chunks created: {stats['chunks_created']}")
    
#     if stats['error_queries']:
#         print(f"\nErrors encountered ({len(stats['error_queries'])}):") 
#         for error in stats['error_queries'][:5]:  # Show first 5
#             print(f"  - {error}")
#         if len(stats['error_queries']) > 5:
#             print(f"  ... and {len(stats['error_queries']) - 5} more")
    
#     print(f"\nTotal documents created: {len(docs)}")
#     return docs



# # def ensure_description_column(csv_path: Union[str, pathlib.Path]) -> bool:
# #     """Ensure the CSV has a 'description' column, add it if missing.
    
# #     Args:
# #         csv_path: Path to the CSV file
        
# #     Returns:
# #         True if column was added, False if it already existed
        
# #     Raises:
# #         Exception: If CSV cannot be read or written
# #     """
# #     if isinstance(csv_path, str):
# #         csv_path = pathlib.Path(csv_path).expanduser().resolve()
    
# #     # Validate file exists and is readable
# #     if not csv_path.exists():
# #         raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
# #     if not csv_path.is_file():
# #         raise ValueError(f"Path is not a file: {csv_path}")
    
# #     # Check file permissions
# #     if not os.access(csv_path, os.R_OK):
# #         raise PermissionError(f"Cannot read CSV file: {csv_path}")
        
# #     if not os.access(csv_path, os.W_OK):
# #         raise PermissionError(f"Cannot write to CSV file: {csv_path}")
    
# #     try:
# #         import pandas as pd
# #         df = pd.read_csv(csv_path)
        
# #         # Validate required 'query' column exists
# #         if 'query' not in df.columns:
# #             raise ValueError(f"CSV file missing required 'query' column. Found columns: {list(df.columns)}")
        
# #         if 'description' in df.columns:
# #             return False  # Column already exists
        
# #         # Add empty description column
# #         df['description'] = ""
        
# #         # Create backup
# #         backup_path = csv_path.with_suffix('.csv.backup')
# #         csv_path.rename(backup_path)
        
# #         # Write updated CSV
# #         df.to_csv(csv_path, index=False)
# #         print(f"Added 'description' column to {csv_path.name}")
        
# #         # Remove backup if successful
# #         backup_path.unlink()
# #         return True
        
#     except Exception as e:
#         # Restore backup if it exists
#         backup_path = csv_path.with_suffix('.csv.backup')
#         if backup_path.exists():
#             backup_path.rename(csv_path)
#         raise Exception(f"Failed to add description column: {e}")


# def find_queries_without_descriptions(csv_path: Union[str, pathlib.Path]) -> List[tuple]:
#     """Find queries in CSV that are missing descriptions.
    
#     Args:
#         csv_path: Path to the CSV file
        
#     Returns:
#         List of tuples: (row_idx, query_text) for queries without descriptions
#     """
#     if isinstance(csv_path, str):
#         csv_path = pathlib.Path(csv_path).expanduser().resolve()
    
#     # Validate file exists and is readable
#     if not csv_path.exists():
#         print(f"Warning: CSV file not found: {csv_path}")
#         return []
    
#     if not os.access(csv_path, os.R_OK):
#         print(f"Warning: Cannot read CSV file: {csv_path}")
#         return []
    
#     queries_needing_descriptions = []
    
#     try:
#         import pandas as pd
#         df = pd.read_csv(csv_path)
        
#         # Validate required 'query' column exists
#         if 'query' not in df.columns:
#             print(f"Error: CSV file missing required 'query' column. Found columns: {list(df.columns)}")
#             return []
        
#         # Ensure description column exists
#         if 'description' not in df.columns:
#             result = []
#             for idx, row in df.iterrows():
#                 query_text = row.get('query', '')
#                 if not pd.isna(query_text) and str(query_text).strip():
#                     result.append((idx, str(query_text).strip()))
#             return result
        
#         # Find rows with empty or missing descriptions
#         for idx, row in df.iterrows():
#             # Handle NaN values properly
#             query_text = row.get('query', '')
#             if pd.isna(query_text):
#                 query_text = ''
#             else:
#                 query_text = str(query_text).strip()
            
#             description = row.get('description', '')
#             if pd.isna(description):
#                 description = ''
#             else:
#                 description = str(description).strip()
            
#             # Debug output
#             print(f"Row {idx}: query_exists={bool(query_text)}, description_exists={bool(description)}, description_value='{description}'")
            
#             if query_text and not description:
#                 queries_needing_descriptions.append((idx, query_text))
#                 print(f"  -> Added row {idx} to queries needing descriptions")
        
#         return queries_needing_descriptions
        
#     except Exception as e:
#         print(f"Error finding queries without descriptions: {e}")
#         return []


# def update_csv_descriptions(csv_path: Union[str, pathlib.Path], 
#                           descriptions: Dict[int, str]) -> bool:
#     """Update CSV file with generated descriptions.
    
#     Args:
#         csv_path: Path to the CSV file
#         descriptions: Dictionary mapping row indices to descriptions
        
#     Returns:
#         True if successful, False otherwise
#     """
#     if isinstance(csv_path, str):
#         csv_path = pathlib.Path(csv_path).expanduser().resolve()
    
#     # Validate file exists and is writable
#     if not csv_path.exists():
#         print(f"Error: CSV file not found: {csv_path}")
#         return False
    
#     if not os.access(csv_path, os.R_OK | os.W_OK):
#         print(f"Error: Insufficient permissions for CSV file: {csv_path}")
#         return False
    
#     if not descriptions:
#         return True  # Nothing to update
    
#     try:
#         import pandas as pd
#         df = pd.read_csv(csv_path)
        
#         # Validate required 'query' column exists
#         if 'query' not in df.columns:
#             print(f"Error: CSV file missing required 'query' column. Found columns: {list(df.columns)}")
#             return False
        
#         # Ensure description column exists
#         if 'description' not in df.columns:
#             df['description'] = ""
        
#         # Create backup
#         backup_path = csv_path.with_suffix('.csv.backup')
#         df.to_csv(backup_path, index=False)
        
#         # Update descriptions
#         for row_idx, description in descriptions.items():
#             if row_idx < len(df):
#                 df.at[row_idx, 'description'] = description
        
#         # Write updated CSV
#         df.to_csv(csv_path, index=False)
        
#         # Remove backup if successful
#         backup_path.unlink()
        
#         print(f"Updated {len(descriptions)} descriptions in {csv_path.name}")
#         return True
        
#     except Exception as e:
#         print(f"Error updating CSV descriptions: {e}")
#         # Restore backup if it exists
#         backup_path = csv_path.with_suffix('.csv.backup')
#         if backup_path.exists():
#             try:
#                 import pandas as pd
#                 backup_df = pd.read_csv(backup_path)
#                 backup_df.to_csv(csv_path, index=False)
#                 backup_path.unlink()
#                 print("Restored CSV from backup after update failure")
#             except Exception as restore_error:
#                 print(f"Failed to restore backup: {restore_error}")
#         return False


# def merge_documents_into_vector_store(
#     vector_store: FAISS,
#     new_documents: List[Document],
#     index_path: pathlib.Path,
#     backup: bool = True
# ) -> FAISS:
#     """Merge new documents into an existing FAISS vector store.
    
#     Args:
#         vector_store: Existing FAISS vector store
#         new_documents: List of new documents to add
#         index_path: Path where the vector store is saved
#         backup: Whether to create a backup before merging
        
#     Returns:
#         Updated FAISS vector store
        
#     Raises:
#         Exception: If merging fails and backup restoration is needed
#     """
#     if not new_documents:
#         print("No new documents to merge.")
#         return vector_store
    
#     print(f"Merging {len(new_documents)} new documents into existing vector store...")
    
#     backup_path = None
#     if backup:
#         # Create backup directory
#         backup_path = index_path.parent / f"{index_path.name}_backup_{int(time.time())}"
#         try:
#             print(f"Creating backup at {backup_path}")
#             backup_path.mkdir(parents=True, exist_ok=True)
#             vector_store.save_local(str(backup_path))
#         except Exception as e:
#             print(f"Warning: Could not create backup: {e}")
#             backup_path = None
    
#     try:
#         # Create embeddings for new documents
#         embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
#         # Extract texts and metadatas from documents
#         texts = [doc.page_content for doc in new_documents]
#         metadatas = [doc.metadata for doc in new_documents]
        
#         print(f"Generating embeddings for {len(texts)} new document chunks...")
        
#         # Add new documents to the existing vector store
#         # FAISS.add_texts() is the method for incremental additions
#         vector_store.add_texts(texts=texts, metadatas=metadatas)
        
#         # Save the updated vector store
#         print(f"Saving updated vector store to {index_path}")
#         vector_store.save_local(str(index_path))
        
#         # Clean up backup if successful
#         if backup_path and backup_path.exists():
#             try:
#                 import shutil
#                 shutil.rmtree(backup_path)
#                 print("Backup cleaned up successfully")
#             except Exception as e:
#                 print(f"Warning: Could not remove backup: {e}")
        
#         print(f"Successfully merged {len(new_documents)} documents into vector store")
#         return vector_store
        
#     except Exception as e:
#         print(f"Error during vector store merge: {e}")
        
#         # Attempt to restore from backup
#         if backup_path and backup_path.exists():
#             try:
#                 print(f"Restoring vector store from backup: {backup_path}")
#                 embeddings = OllamaEmbeddings(model="nomic-embed-text")
#                 restored_store = FAISS.load_local(
#                     str(backup_path),
#                     embeddings,
#                     allow_dangerous_deserialization=True
#                 )
                
#                 # Save restored backup to original location
#                 restored_store.save_local(str(index_path))
#                 print("Vector store restored from backup")
                
#                 # Clean up backup
#                 import shutil
#                 shutil.rmtree(backup_path)
                
#                 # Re-raise the original error
#                 raise Exception(f"Vector store merge failed, restored from backup: {e}")
                
#             except Exception as restore_error:
#                 print(f"Failed to restore from backup: {restore_error}")
#                 raise Exception(f"Vector store merge failed and backup restoration failed: {e}")
#         else:
#             raise Exception(f"Vector store merge failed and no backup available: {e}")

def _get_llm_client():
    """Return an Ollama chat client.
    
    No authentication required for local Ollama instance.
    """
    return genai_client

def answer_question(
    query: str,
    vector_store: FAISS = None,
    k: int = 4,
    *,
    return_docs: bool = False,
    return_tokens: bool = False,
    source_directory: pathlib.Path = None,
    index_directory: pathlib.Path = None,
    csv_path: Optional[Union[str, pathlib.Path]] = None,
    batch_size: int = 100,
    max_workers: int = 8
):
    """Answer a user question using Retrieval-Augmented Generation.

    Args:
        query: The user's question.
        vector_store: The FAISS vector store to search. If None, will build/load from directories or CSV.
        k: Number of relevant chunks to retrieve.
        return_docs: Whether to return the retrieved documents.
        return_tokens: Whether to return token usage information.
        source_directory: Path to directory containing SQL files (if vector_store is None).
        index_directory: Path to directory for storing FAISS index (if vector_store is None).
        csv_path: Path to CSV file with 'query' column (if vector_store is None and CSV mode desired).
        batch_size: Number of documents to process per batch for parallel processing (default: 100).
        max_workers: Maximum number of parallel workers (default: 4).

    Returns:
        The LLM-generated answer leveraging retrieved context.
        If return_docs=True, returns (answer, docs).
        If return_tokens=True, returns token usage info as well.
    """
    # Build or load vector store if not provided
    if vector_store is None:
        vector_store = build_or_load_vector_store(
            source_directory=source_directory,
            index_directory=index_directory,
            csv_path=csv_path,
            force_rebuild=False,
            batch_size=batch_size,
            max_workers=max_workers
        )
    # Retrieve relevant context from the provided vector store
    retrieved_docs = vector_store.similarity_search(query, k=k)

    context = "\n\n".join(
        [f"Source: {doc.metadata['source']}\n{doc.page_content}" for doc in retrieved_docs]
    )

    answer_text, token_usage=generate_answer_from_context(query, context)
    # prompt = (
    #     "You are an expert SQL analyst helping answer questions about a retail analytics codebase. "
    #     "Use ONLY the provided context to answer the user's question. If the answer is not contained "
    #     "within the context, respond with 'I don't know based on the provided context.'\n\n"
    #     f"Context:\n{context}\n\nUser question: {query}\n\nAnswer:"
    # )

    # client = _get_llm_client()

    # Resilient call with simple exponential backoff
    # retries = 3
    # completion = None
    # for attempt in range(1, retries + 1):
    #     try:
    #         response = client.models.generate_content(
    #             model=GENAI_MODEL_NAME,
    #             contents=prompt
    #         )
    #         answer_text = response.text.strip()
            
    #         # Estimate token usage (Google GenAI doesn't provide detailed counts)
    #         prompt_tokens = len(prompt.split()) * 1.3  # Rough estimate
    #         completion_tokens = len(answer_text.split()) * 1.3  # Rough estimate
    #         token_usage = {
    #             'prompt_tokens': int(prompt_tokens),
    #             'completion_tokens': int(completion_tokens),
    #             'total_tokens': int(prompt_tokens + completion_tokens),
    #             'model': GENAI_MODEL_NAME
    #         }
    #         break  # success → exit loop
    #     except Exception as exc:  # covers connection and other errors
    #         if attempt == retries:
    #             raise  # re-throw after last attempt
    #         wait_secs = 2 ** attempt
    #         print(f"Google GenAI API error ({exc}). Retrying in {wait_secs}s …")
    #         time.sleep(wait_secs)


    # Return based on flags
    if return_docs and return_tokens:
        return answer_text, retrieved_docs, token_usage
    elif return_docs:
        return answer_text, retrieved_docs
    elif return_tokens:
        return answer_text, token_usage
    return answer_text


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Simple RAG over SQL documentation")
    parser.add_argument("question", type=str, help="Question to ask the RAG system")
    parser.add_argument("--k", type=int, default=4, help="Number of chunks to retrieve")
    parser.add_argument("--source-dir", type=str, default=None, 
                       help="Path to directory containing SQL files (defaults to retail_system)")
    parser.add_argument("--index-dir", type=str, default=None,
                       help="Path to directory for storing FAISS indices (defaults to faiss_indices)")
    parser.add_argument("--csv", type=str, default=None,
                       help="Path to CSV file with 'query' column containing SQL queries")
    parser.add_argument("--batch-size", type=int, default=100,
                       help="Batch size for parallel processing (default: 100)")
    parser.add_argument("--max-workers", type=int, default=4,
                       help="Maximum number of parallel workers (default: 4)")
    args = parser.parse_args()

    source_dir = pathlib.Path(args.source_dir).expanduser().resolve() if args.source_dir else None
    index_dir = pathlib.Path(args.index_dir).expanduser().resolve() if args.index_dir else None
    csv_file = pathlib.Path(args.csv).expanduser().resolve() if args.csv else None

    # Validation: can't use both CSV and source directory
    if csv_file and source_dir:
        print("Error: Cannot specify both --csv and --source-dir. Choose one.")
        sys.exit(1)

    answer, docs, token_usage = answer_question(
        args.question, 
        k=args.k, 
        return_docs=True, 
        return_tokens=True,
        source_directory=source_dir,
        index_directory=index_dir,
        csv_path=csv_file,
        batch_size=args.batch_size,
        max_workers=args.max_workers
    )

    print("\n=== Answer ===\n")
    print(answer)

    print("\n=== Sources ===")
    for doc in docs:
        print(f"\nFile: {doc.metadata['source']} (chunk {doc.metadata['chunk']})\n{doc.page_content}")

    print("\n=== Token Usage ===")
    print(token_usage) 