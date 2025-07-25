import os
import pathlib
import pickle
from typing import List
import time
import re

from dotenv import load_dotenv, find_dotenv
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_ollama import ChatOllama
import streamlit as st

# Load .env regardless of current working directory
load_dotenv(find_dotenv(), override=False)

# Default paths - can be overridden by function parameters
DEFAULT_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "retail_system"
DEFAULT_INDEX_DIR = pathlib.Path(__file__).resolve().parent / "faiss_indices"
LLM_MODEL_NAME = "phi3"  # Ollama Phi3 model

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


def _build_or_load_vector_store(source_directory: pathlib.Path = None, index_directory: pathlib.Path = None) -> FAISS:
    """
    Build a FAISS vector store using the recommended save_local/load_local methods,
    or load it from a local directory if it already exists.
    
    Args:
        source_directory: Path to directory containing SQL files. Defaults to DEFAULT_DATA_DIR.
        index_directory: Path to directory for storing FAISS index. Defaults to DEFAULT_INDEX_DIR.
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
    
    # Create unique index path based on source directory
    # Use a simpler approach - just the directory name and a short path identifier
    source_name = source_directory.name
    # Use last 2 parts of path to make it more unique
    path_parts = source_directory.parts[-2:] if len(source_directory.parts) >= 2 else source_directory.parts
    path_identifier = "_".join(path_parts).replace(" ", "_")
    index_path = index_directory / f"index_{path_identifier}"
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    if index_path.exists() and index_path.is_dir():
        print(f"Loading existing FAISS index from {index_path}")
        # allow_dangerous_deserialization is required for loading pickled objects
        return FAISS.load_local(
            str(index_path),
            embeddings,
            allow_dangerous_deserialization=True
        )

    print("Building new FAISS index...")
    documents = _load_source_files(source_directory)
    if not documents:
         raise ValueError(
            f"No source documents found. Ensure the directory '{source_directory}' "
            "contains .sql or .py files."
        )

    vector_store = FAISS.from_documents(documents, embeddings)

    # Ensure index directory exists
    index_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Persist index locally for future runs using the recommended method
    print(f"Saving new FAISS index to {index_path}")
    vector_store.save_local(str(index_path))
    return vector_store


def _get_llm_client() -> ChatOllama:
    """Return an Ollama chat client.
    
    No authentication required for local Ollama instance.
    """
    return ChatOllama(model=LLM_MODEL_NAME, temperature=0.2)


def answer_question(
    query: str,
    vector_store: FAISS = None,
    k: int = 4,
    *,
    return_docs: bool = False,
    return_tokens: bool = False,
    source_directory: pathlib.Path = None,
    index_directory: pathlib.Path = None
):
    """Answer a user question using Retrieval-Augmented Generation.

    Args:
        query: The user's question.
        vector_store: The FAISS vector store to search. If None, will build/load from directories.
        k: Number of relevant chunks to retrieve.
        return_docs: Whether to return the retrieved documents.
        return_tokens: Whether to return token usage information.
        source_directory: Path to directory containing SQL files (if vector_store is None).
        index_directory: Path to directory for storing FAISS index (if vector_store is None).

    Returns:
        The LLM-generated answer leveraging retrieved context.
        If return_docs=True, returns (answer, docs).
        If return_tokens=True, returns token usage info as well.
    """
    # Build or load vector store if not provided
    if vector_store is None:
        vector_store = _build_or_load_vector_store(source_directory, index_directory)
    # Retrieve relevant context from the provided vector store
    retrieved_docs = vector_store.similarity_search(query, k=k)

    context = "\n\n".join(
        [f"Source: {doc.metadata['source']}\n{doc.page_content}" for doc in retrieved_docs]
    )

    prompt = (
        "You are an expert SQL analyst helping answer questions about a retail analytics codebase. "
        "Use ONLY the provided context to answer the user's question. If the answer is not contained "
        "within the context, respond with 'I don't know based on the provided context.'\n\n"
        f"Context:\n{context}\n\nUser question: {query}\n\nAnswer:"
    )

    client = _get_llm_client()

    # Resilient call with simple exponential backoff
    retries = 3
    completion = None
    for attempt in range(1, retries + 1):
        try:
            response = client.invoke(prompt)
            answer_text = response.content.strip()
            completion = response  # Store for token usage extraction
            break  # success → exit loop
        except Exception as exc:  # covers connection and other errors
            if attempt == retries:
                raise  # re-throw after last attempt
            wait_secs = 2 ** attempt
            print(f"Ollama API error ({exc}). Retrying in {wait_secs}s …")
            time.sleep(wait_secs)

    # Extract token usage - Ollama doesn't provide detailed token counts
    # Provide approximate counts based on text length
    token_usage = None
    if completion:
        prompt_tokens = len(prompt.split()) * 1.3  # Rough estimate
        completion_tokens = len(answer_text.split()) * 1.3  # Rough estimate
        token_usage = {
            'prompt_tokens': int(prompt_tokens),
            'completion_tokens': int(completion_tokens),
            'total_tokens': int(prompt_tokens + completion_tokens),
            'model': LLM_MODEL_NAME
        }

    # Return based on flags
    if return_docs and return_tokens:
        return answer_text, retrieved_docs, token_usage
    elif return_docs:
        return answer_text, retrieved_docs
    elif return_tokens:
        return answer_text, token_usage
    return answer_text


def generate_description(query_text: str, model: str = "phi3") -> tuple[str, dict]:
    """Generate a description for a SQL query and return token usage.
    
    Args:
        query_text: The SQL query text to describe
        model: The model to use for description generation
        
    Returns:
        A tuple of (description, token_usage_dict)
    """
    prompt = (
        "Summarize the following SQL query in at most two sentences of plain English. "
        "Focus on the business purpose, key tables and metrics.\n\n" + query_text[:4000]
    )
    
    try:
        client = ChatOllama(model=model, temperature=0.3)
        response = client.invoke(prompt)
        description = response.content.strip()
        
        # Extract token usage - approximate for Ollama
        prompt_tokens = len(prompt.split()) * 1.3
        completion_tokens = len(description.split()) * 1.3
        token_usage = {
            'prompt_tokens': int(prompt_tokens),
            'completion_tokens': int(completion_tokens),
            'total_tokens': int(prompt_tokens + completion_tokens),
            'model': model
        }
        
        return description, token_usage
        
    except Exception as exc:
        return f"Description unavailable ({exc})", {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'model': model
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simple RAG over SQL documentation")
    parser.add_argument("question", type=str, help="Question to ask the RAG system")
    parser.add_argument("--k", type=int, default=4, help="Number of chunks to retrieve")
    parser.add_argument("--source-dir", type=str, default=None, 
                       help="Path to directory containing SQL files (defaults to retail_system)")
    parser.add_argument("--index-dir", type=str, default=None,
                       help="Path to directory for storing FAISS indices (defaults to faiss_indices)")
    args = parser.parse_args()

    source_dir = pathlib.Path(args.source_dir).expanduser().resolve() if args.source_dir else None
    index_dir = pathlib.Path(args.index_dir).expanduser().resolve() if args.index_dir else None

    answer, docs, token_usage = answer_question(
        args.question, 
        k=args.k, 
        return_docs=True, 
        return_tokens=True,
        source_directory=source_dir,
        index_directory=index_dir
    )

    print("\n=== Answer ===\n")
    print(answer)

    print("\n=== Sources ===")
    for doc in docs:
        print(f"\nFile: {doc.metadata['source']} (chunk {doc.metadata['chunk']})\n{doc.page_content}")

    print("\n=== Token Usage ===")
    print(token_usage) 