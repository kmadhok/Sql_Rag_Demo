#!/usr/bin/env python3
"""
OpenAI Embedding Generator (CSV → FAISS)

Builds a FAISS vector store from a CSV with a 'query' column using OpenAI embeddings.
Saves to faiss_indices/index_<csv_stem> so the existing apps can load it.

Usage:
  export OPENAI_API_KEY=...  # required
  python openai_embedding_generator.py --csv sample_queries_with_metadata.csv

Optional env vars:
  OPENAI_EMBEDDING_MODEL (default: text-embedding-3-small)
"""

import argparse
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from utils.embedding_provider import get_embedding_function

load_dotenv()


def build_documents(df: pd.DataFrame) -> List[Document]:
    docs: List[Document] = []
    if 'query' not in df.columns:
        raise ValueError("CSV must contain a 'query' column")

    for i, row in df.iterrows():
        query = str(row.get('query', '') or '').strip()
        if not query:
            continue
        description = str(row.get('description', '') or '').strip()
        content = f"Query: {query}"
        if description:
            content += f"\nDescription: {description}"
        docs.append(Document(page_content=content, metadata={"row": i}))
    return docs


def main():
    ap = argparse.ArgumentParser(description="Generate FAISS store with OpenAI embeddings from CSV")
    ap.add_argument("--csv", required=True, help="Path to CSV with a 'query' column")
    ap.add_argument("--output", default="faiss_indices", help="Output directory for vector store")
    args = ap.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    out_dir = Path(args.output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Force OpenAI provider
    os.environ.setdefault("EMBEDDINGS_PROVIDER", "openai")

    # Validate API key
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY env var is required for OpenAI embeddings")

    df = pd.read_csv(csv_path)
    docs = build_documents(df)
    if not docs:
        raise RuntimeError("No valid queries found in CSV")

    embeddings = get_embedding_function(provider="openai")

    print(f"🔧 Creating FAISS vector store for {len(docs)} documents using OpenAI embeddings...")
    store = FAISS.from_documents(docs, embeddings)

    index_name = f"index_{csv_path.stem}"
    target = out_dir / index_name
    store.save_local(str(target))
    print(f"✅ Saved vector store to {target}")


if __name__ == "__main__":
    main()

