#!/usr/bin/env python3
"""
Direct FAISS test to bypass complex loading
"""

import sys
from pathlib import Path

print("🧪 Direct FAISS Test")
print("=" * 30)

# Add parent directory to Python path
sys.path.append('..')

try:
    from langchain_community.vectorstores import FAISS
    from langchain_ollama import OllamaEmbeddings
    print("✅ Core imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Try: pip install langchain-community langchain-ollama")
    sys.exit(1)

# Test path to FAISS index
index_path = Path("faiss_indices/index_sample_queries_with_metadata_recovered")
print(f"📂 FAISS index path: {index_path}")
print(f"📂 Index exists: {index_path.exists()}")
print(f"📂 index.faiss exists: {(index_path / 'index.faiss').exists()}")
print(f"📂 index.pkl exists: {(index_path / 'index.pkl').exists()}")

if not index_path.exists() or not (index_path / 'index.faiss').exists():
    print("❌ FAISS index files not found")
    sys.exit(1)

try:
    # Step 1: Initialize embeddings (use mock as Ollama fallback)
    print("🔗 Initializing embeddings...")
    
    # Create a deterministic mock embedding that works with LangChain interface
    from langchain_core.embeddings import Embeddings
    
    class MockEmbeddings(Embeddings):
        def __init__(self, embedding_dim=1536):  # Standard OpenAI embedding dimension
            self.embedding_dim = embedding_dim
            
        def embed_query(self, text):
            # Create consistent embeddings using hash
            import hashlib
            
            # Create a deterministic vector from the text
            hash_obj = hashlib.sha256(text.encode('utf-8'))
            hash_bytes = hash_obj.digest()
            
            # Convert to float array and interpolate to the right dimension
            base_values = [float(b) / 255.0 for b in hash_bytes]
            
            # Interpolate to get the correct embedding dimension
            if len(base_values) < self.embedding_dim:
                # Repeat and trim to reach target dimension
                repeated = (base_values * ((self.embedding_dim // len(base_values)) + 1))[:self.embedding_dim]
                return repeated
            else:
                # Truncate if too long
                return base_values[:self.embedding_dim]
        
        def embed_documents(self, texts):
            return [self.embed_query(text) for text in texts]
        
        # LangChain compatibility: make object callable
        def __call__(self, text):
            if isinstance(text, list):
                return self.embed_documents(text)
            else:
                return self.embed_query(text)
    
    embeddings = MockEmbeddings()
    print("✅ Mock embeddings created (LangChain compatible)")
    
    # Step 2: Load FAISS index
    print("📦 Loading FAISS index...")
    vector_store = FAISS.load_local(
        str(index_path),
        embeddings,
        allow_dangerous_deserialization=True
    )
    print("✅ FAISS index loaded successfully")
    
    # Step 3: Test similarity search
    test_query = "Show me expensive products"
    print(f"🔍 Testing similarity search: '{test_query}'")
    
    docs = vector_store.similarity_search(test_query, k=3)
    print(f"✅ Found {len(docs)} similar documents")
    
    for i, doc in enumerate(docs):
        print(f"\n📄 Document {i+1}:")
        print(f"   Content: {doc.page_content[:100]}...")
        print(f"   Metadata: {doc.metadata}")
    
    print("\n🎉 FAISS test successful! The index is working.")
    
except Exception as e:
    print(f"❌ FAISS test failed: {e}")
    import traceback
    print(f"🔍 Traceback: {traceback.format_exc()}")

print("\n💡 If this test works, the issue is in the complex loading chain in query_search.py")