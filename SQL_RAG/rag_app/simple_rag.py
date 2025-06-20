import os
import pathlib
import pickle
from typing import List
import time

from dotenv import load_dotenv
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores.faiss import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import groq
from groq import Groq

# Load environment variables from .env if present
load_dotenv()

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "retail_system"
INDEX_PATH = pathlib.Path(__file__).resolve().parent / "faiss_index.pkl"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL_NAME = "llama3-70b-8192"  # Adjust to the exact Groq model name if different


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
    """Build a FAISS vector store (or load if cached)."""
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "rb") as f:
            return pickle.load(f)

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    documents = _load_source_files()
    vector_store = FAISS.from_documents(documents, embeddings)

    # Persist index locally for future runs
    with open(INDEX_PATH, "wb") as f:
        pickle.dump(vector_store, f)
    return vector_store


def _get_llm_client() -> Groq:
    """Initialize Groq client using the GROQ_API_KEY env variable."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("Please set the GROQ_API_KEY environment variable.")
    return Groq(api_key=api_key)


def answer_question(query: str, k: int = 4, *, return_docs: bool = False):
    """Answer a user question using Retrieval-Augmented Generation.

    Args:
        query: The user's question.
        k: Number of relevant chunks to retrieve.
        return_docs: Whether to return the retrieved documents.

    Returns:
        The LLM-generated answer leveraging retrieved context.
    """
    # Retrieve relevant context
    vector_store = _build_or_load_vector_store()
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

    if return_docs:
        return answer_text, retrieved_docs
    return answer_text


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simple RAG over retail_system SQL docs")
    parser.add_argument("question", type=str, help="Question to ask the RAG system")
    parser.add_argument("--k", type=int, default=4, help="Number of chunks to retrieve")
    args = parser.parse_args()

    answer, docs = answer_question(args.question, k=args.k, return_docs=True)

    print("\n=== Answer ===\n")
    print(answer)

    print("\n=== Sources ===")
    for doc in docs:
        print(f"\nFile: {doc.metadata['source']} (chunk {doc.metadata['chunk']})\n{doc.page_content}") 