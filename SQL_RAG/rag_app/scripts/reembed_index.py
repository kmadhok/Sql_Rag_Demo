#!/usr/bin/env python3
"""
Re-embed an existing FAISS index with the currently configured embedding provider.

The documents (page_content + metadata) are read from the source index's docstore,
so the new index holds exactly the same content; only the vectors change.

Usage (from rag_app/):
  EMBEDDINGS_PROVIDER=openrouter python scripts/reembed_index.py \
      --source index_sample_queries_with_metadata_recovered \
      --output index_sample_queries_openrouter
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_community.vectorstores import FAISS  # noqa: E402
from langchain_core.embeddings import Embeddings  # noqa: E402

from data.app_data_loader import FAISS_INDICES_DIR  # noqa: E402
from utils.embedding_provider import get_embedding_function, get_provider_info  # noqa: E402


class _NoEmbeddings(Embeddings):
    """Placeholder so the source index can be loaded without calling any API."""

    def embed_documents(self, texts):
        raise RuntimeError("source index is read-only here")

    def embed_query(self, text):
        raise RuntimeError("source index is read-only here")


def load_documents(source_dir: Path):
    store = FAISS.load_local(str(source_dir), _NoEmbeddings(), allow_dangerous_deserialization=True)
    return [store.docstore.search(doc_id) for doc_id in store.index_to_docstore_id.values()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="existing index directory name under faiss_indices/")
    parser.add_argument("--output", required=True, help="new index directory name under faiss_indices/")
    args = parser.parse_args()

    source_dir = FAISS_INDICES_DIR / args.source
    output_dir = FAISS_INDICES_DIR / args.output
    if not source_dir.exists():
        print(f"Source index not found: {source_dir}", file=sys.stderr)
        return 1

    docs = load_documents(source_dir)
    print(f"Loaded {len(docs)} documents from {source_dir}")
    print(f"Embedding with {get_provider_info()}")

    store = FAISS.from_documents(docs, get_embedding_function())
    store.save_local(str(output_dir))
    print(f"Saved {store.index.ntotal} vectors (dim={store.index.d}) to {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
