import os
import pathlib
import pickle
from typing import List
import time

from dotenv import load_dotenv, find_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores.faiss import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import groq
from groq import Groq
import streamlit as st

# Load .env regardless of current working directory
load_dotenv(find_dotenv(), override=False)

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "retail_system"
INDEX_PATH = pathlib.Path(__file__).resolve().parent / "faiss_index"
LLM_MODEL_NAME = "llama-3.3-70b-versatile"  # Adjust to the exact Groq model name if different


def _load_source_files() -> List[Document]:
    """Walk the retail_system directory and load .sql and .py files as Documents."""
    docs: List[Document] = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    for file_path in DATA_DIR.rglob("*.*"):
        if file_path.suffix.lower() not in {".sql", ".py"}:
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Skipping {file_path} due to read error: {e}")
            continue

        # Split into chunks
        for i, chunk in enumerate(splitter.split_text(text)):
            metadata = {
                "source": str(file_path.relative_to(DATA_DIR)),
                "chunk": i,
            }
            docs.append(Document(page_content=chunk, metadata=metadata))
    return docs


def _build_or_load_vector_store() -> FAISS:
    """
    Build a FAISS vector store using the recommended save_local/load_local methods,
    or load it from a local directory if it already exists.
    """
    embeddings = OpenAIEmbeddings()

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


def _get_llm_client() -> Groq:
    """Return an authenticated Groq client.

    Tries several common env-var names (useful if the key is stored as, e.g.,
    GROQ_KEY or GROQ_TOKEN). Provides a clear hint if none are found.
    """

    api_key = (
        os.getenv("GROQ_API_KEY")
        or os.getenv("GROQ_KEY")
        or os.getenv("GROQ_TOKEN")
    )

    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not found. Please set it in your environment or a .env file."
        )

    return Groq(api_key=api_key)


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
            completion = client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.2,
            )
            answer_text = completion.choices[0].message.content.strip()
            break  # success → exit loop
        except groq.APIError as exc:  # covers connection + status errors
            if attempt == retries:
                raise  # re-throw after last attempt
            wait_secs = 2 ** attempt
            print(f"Groq API error ({exc}). Retrying in {wait_secs}s …")
            time.sleep(wait_secs)

    # Extract token usage if available
    token_usage = None
    if completion and hasattr(completion, 'usage'):
        token_usage = {
            'prompt_tokens': completion.usage.prompt_tokens,
            'completion_tokens': completion.usage.completion_tokens,
            'total_tokens': completion.usage.total_tokens,
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


def generate_description(query_text: str, model: str = "llama3-8b-8192") -> tuple[str, dict]:
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
        client = _get_llm_client()
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.3,
        )
        description = completion.choices[0].message.content.strip()
        
        # Extract token usage
        token_usage = {
            'prompt_tokens': completion.usage.prompt_tokens if hasattr(completion, 'usage') else 0,
            'completion_tokens': completion.usage.completion_tokens if hasattr(completion, 'usage') else 0,
            'total_tokens': completion.usage.total_tokens if hasattr(completion, 'usage') else 0,
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
