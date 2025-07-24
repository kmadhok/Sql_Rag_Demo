import os
import pathlib
import pickle
from typing import List
import time

from dotenv import load_dotenv, find_dotenv
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_ollama import ChatOllama
import streamlit as st

# Load .env regardless of current working directory
load_dotenv(find_dotenv(), override=False)

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "retail_system"
INDEX_PATH = pathlib.Path(__file__).resolve().parent / "faiss_index"
LLM_MODEL_NAME = "phi3"  # Ollama Phi3 model


def _load_source_files() -> List[Document]:
    """Walk the retail_system directory and load .sql and .py files as Documents.
    
    Enhanced version that:
    - Recursively walks through nested folder structures
    - Avoids virtual environment and cache directories
    - Provides better logging and file organization
    - Extracts SQL from Python files with enhanced context
    """
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
            
        # Check patterns
        if (dir_name.startswith('.') and len(dir_name) > 1 and 
            dir_name not in {'.sql', '.py'}):  # Skip hidden dirs but not file extensions
            return True
            
        if dir_name.endswith('_env') or dir_name.endswith('_cache'):
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
    
    def process_directory(dir_path: pathlib.Path) -> None:
        """Recursively process directory and its subdirectories."""
        if should_skip_directory(dir_path):
            stats['folders_skipped'] += 1
            print(f"Skipping excluded directory: {dir_path.relative_to(DATA_DIR)}")
            return
        
        stats['folders_processed'] += 1
        print(f"Processing directory: {dir_path.relative_to(DATA_DIR)}")
        
        # Process files in current directory
        for file_path in dir_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in {".sql", ".py"}:
                try:
                    text = file_path.read_text(encoding="utf-8")
                    relative_path = str(file_path.relative_to(DATA_DIR))
                    
                    if file_path.suffix.lower() == ".sql":
                        stats['sql_files_found'] += 1
                        # Process SQL files directly
                        for i, chunk in enumerate(splitter.split_text(text)):
                            metadata = {
                                "source": relative_path,
                                "chunk": i,
                                "file_type": "direct_sql",
                                "folder_path": str(file_path.parent.relative_to(DATA_DIR))
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
                                        "folder_path": str(file_path.parent.relative_to(DATA_DIR)),
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
                                    "folder_path": str(file_path.parent.relative_to(DATA_DIR))
                                }
                                docs.append(Document(page_content=chunk, metadata=metadata))
                                stats['total_chunks_created'] += 1
                    
                except Exception as e:
                    stats['skipped_files'].append(f"{relative_path}: {e}")
                    print(f"Skipping {relative_path} due to read error: {e}")
        
        # Recursively process subdirectories
        for subdir in dir_path.iterdir():
            if subdir.is_dir():
                process_directory(subdir)
    
    print(f"Starting enhanced file discovery in: {DATA_DIR}")
    process_directory(DATA_DIR)
    
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


def _build_or_load_vector_store() -> FAISS:
    """
    Build a FAISS vector store using the recommended save_local/load_local methods,
    or load it from a local directory if it already exists.
    """
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    if INDEX_PATH.exists() and INDEX_PATH.is_dir():
        print(f"Loading existing FAISS index from {INDEX_PATH}")
        # allow_dangerous_deserialization is required for loading pickled objects
        return FAISS.load_local(
            str(INDEX_PATH),
            embeddings,
            allow_dangerous_deserialization=True
        )

    print("Building new FAISS index...")
    documents = _load_source_files()
    if not documents:
         raise ValueError(
            "No source documents found. Ensure the 'retail_system' directory "
            "contains .sql or .py files."
        )

    vector_store = FAISS.from_documents(documents, embeddings)

    # Persist index locally for future runs using the recommended method
    print(f"Saving new FAISS index to {INDEX_PATH}")
    vector_store.save_local(str(INDEX_PATH))
    return vector_store


def _get_llm_client() -> ChatOllama:
    """Return an Ollama chat client.
    
    No authentication required for local Ollama instance.
    """
    return ChatOllama(model=LLM_MODEL_NAME, temperature=0.2)


def answer_question(
    query: str,
    vector_store: FAISS,
    k: int = 4,
    *,
    return_docs: bool = False,
    return_tokens: bool = False
):
    """Answer a user question using Retrieval-Augmented Generation.

    Args:
        query: The user's question.
        vector_store: The FAISS vector store to search.
        k: Number of relevant chunks to retrieve.
        return_docs: Whether to return the retrieved documents.
        return_tokens: Whether to return token usage information.

    Returns:
        The LLM-generated answer leveraging retrieved context.
        If return_docs=True, returns (answer, docs).
        If return_tokens=True, returns token usage info as well.
    """
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

    parser = argparse.ArgumentParser(description="Simple RAG over retail_system SQL docs")
    parser.add_argument("question", type=str, help="Question to ask the RAG system")
    parser.add_argument("--k", type=int, default=4, help="Number of chunks to retrieve")
    args = parser.parse_args()

    vector_store = _build_or_load_vector_store()
    answer, docs, token_usage = answer_question(args.question, vector_store, k=args.k, return_docs=True, return_tokens=True)

    print("\n=== Answer ===\n")
    print(answer)

    print("\n=== Sources ===")
    for doc in docs:
        print(f"\nFile: {doc.metadata['source']} (chunk {doc.metadata['chunk']})\n{doc.page_content}")

    print("\n=== Token Usage ===")
    print(token_usage) 