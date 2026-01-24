#!/usr/bin/env python3
"""
Setup Script for Integration Tests

Generates a test vector store from sample CSV data using OpenAI embeddings.
This vector store is used by integration tests to validate the complete RAG pipeline.

Usage:
    # Set API key
    export OPENAI_API_KEY=your_key_here

    # Run setup
    python tests/integration/setup_test_vector_store.py

    # Or from project root
    python -m tests.integration.setup_test_vector_store

Requirements:
    - OPENAI_API_KEY environment variable
    - Sample CSV at rag_app/data_new/sample_queries_with_metadata_recovered.csv

Output:
    - Creates tests/integration/test_vector_store/ with FAISS index
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "rag_app"))

print(f"Project root: {project_root}")
print(f"Python path includes: {project_root / 'rag_app'}")

# Check dependencies
try:
    import pandas as pd
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document
    from utils.embedding_provider import get_embedding_function
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("\nInstall required packages:")
    print("  pip install -r requirements.txt")
    print("  pip install -r requirements-test.txt")
    sys.exit(1)

# Load environment variables
load_dotenv()


def validate_environment():
    """Validate required environment variables and files"""
    errors = []

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY environment variable not set")

    # Check sample CSV
    csv_path = project_root / "rag_app" / "data_new" / "sample_queries_with_metadata_recovered.csv"
    if not csv_path.exists():
        errors.append(f"Sample CSV not found: {csv_path}")

    if errors:
        print("❌ Setup validation failed:\n")
        for error in errors:
            print(f"  - {error}")
        print("\nFix these issues and try again.")
        sys.exit(1)

    return csv_path


def build_documents(df: pd.DataFrame) -> list:
    """Build LangChain Documents from CSV"""
    docs = []

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

        # Include metadata
        metadata = {
            "row": i,
            "query": query
        }

        # Add tables if present
        if 'tables' in row and row['tables']:
            metadata["tables"] = row['tables']

        # Add joins if present
        if 'joins' in row and row['joins']:
            metadata["joins"] = row['joins']

        docs.append(Document(page_content=content, metadata=metadata))

    return docs


def main():
    """Generate test vector store"""
    print("=" * 70)
    print("Integration Test Vector Store Setup")
    print("=" * 70)
    print()

    # Validate environment
    print("Validating environment...")
    csv_path = validate_environment()
    print("✅ Environment OK")
    print()

    # Define output path
    output_dir = Path(__file__).parent / "test_vector_store"

    # Load CSV
    print(f"Loading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df)} rows")
    print()

    # Build documents
    print("Building documents...")
    docs = build_documents(df)
    print(f"✅ Created {len(docs)} documents")
    print()

    # Get embedding function
    print("Initializing OpenAI embeddings...")
    os.environ.setdefault("EMBEDDINGS_PROVIDER", "openai")
    embeddings = get_embedding_function(provider="openai")
    print("✅ Embeddings initialized")
    print()

    # Create vector store
    print(f"Creating FAISS vector store...")
    print(f"This may take a minute for {len(docs)} documents...")
    store = FAISS.from_documents(docs, embeddings)
    print("✅ Vector store created")
    print()

    # Save to disk
    print(f"Saving to: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    store.save_local(str(output_dir))
    print("✅ Vector store saved")
    print()

    # Validate by loading
    print("Validating saved vector store...")
    loaded_store = FAISS.load_local(
        str(output_dir),
        embeddings,
        allow_dangerous_deserialization=True
    )
    print("✅ Vector store loads successfully")
    print()

    # Test a sample query
    print("Testing sample query...")
    test_question = "Show me the most expensive products"
    results = loaded_store.similarity_search(test_question, k=3)
    print(f"✅ Sample query returned {len(results)} results")
    print()
    print("Top result:")
    print(f"  {results[0].page_content[:100]}...")
    print()

    # Summary
    print("=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)
    print()
    print("Test vector store created at:")
    print(f"  {output_dir.absolute()}")
    print()
    print("You can now run integration tests:")
    print("  pytest tests/integration/ -v -m integration")
    print()
    print("Or run specific tests:")
    print("  pytest tests/integration/test_complete_pipeline.py::TestCompleteRAGPipeline::test_simple_product_query -v")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
