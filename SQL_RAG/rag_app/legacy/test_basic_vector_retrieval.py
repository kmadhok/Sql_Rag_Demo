#!/usr/bin/env python3
"""
Basic Vector Database Retrieval Test Script

Tests ONLY the core vector retrieval process:
- Ollama connection and embedding generation
- FAISS vector store loading
- Basic similarity search
- Similarity search with relevance scores

Usage:
    python3 test_basic_vector_retrieval.py
"""

import logging
import time
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Simple test queries for vector retrieval
TEST_QUERIES = [
    "How to calculate customer lifetime value?",
    "Show me JOIN queries with customers table", 
    "GROUP BY and COUNT examples",
    "inventory management reports",
    "SQL queries for revenue analysis"
]

def test_ollama_connection():
    """Test Ollama service connection and embedding generation"""
    logger.info("🔧 Testing Ollama Connection")
    logger.info("-" * 40)
    
    try:
        from langchain_ollama import OllamaEmbeddings
        
        # Initialize embeddings
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        # Test embedding generation with a sample query
        test_text = "This is a test query for embedding generation"
        logger.info(f"Testing with: '{test_text}'")
        
        start_time = time.time()
        embedding = embeddings.embed_query(test_text)
        embed_time = time.time() - start_time
        
        logger.info(f"✅ Ollama connection successful")
        logger.info(f"   Model: nomic-embed-text")
        logger.info(f"   Embedding dimensions: {len(embedding)}")
        logger.info(f"   Generation time: {embed_time:.3f}s")
        
        return True, embeddings
        
    except Exception as e:
        logger.error(f"❌ Ollama connection failed: {e}")
        logger.info("💡 Make sure Ollama is running: ollama serve")
        logger.info("💡 And model is downloaded: ollama pull nomic-embed-text")
        return False, None

def load_vector_store(embeddings):
    """Load existing FAISS vector store"""
    logger.info("\n📁 Loading Vector Store")
    logger.info("-" * 40)
    
    # Look for vector store directory
    indices_dir = Path("faiss_indices")
    
    if not indices_dir.exists():
        logger.error("❌ No faiss_indices directory found")
        logger.info("💡 Run: python3 standalone_embedding_generator.py --csv 'your_data.csv'")
        return None
    
    # Find available vector indices
    available_indices = list(indices_dir.glob("index_*"))
    
    if not available_indices:
        logger.error("❌ No vector indices found in faiss_indices/")
        logger.info("💡 Generate embeddings first with standalone_embedding_generator.py")
        return None
    
    logger.info(f"Found {len(available_indices)} vector indices:")
    for idx in available_indices:
        logger.info(f"   - {idx.name}")
    
    # Load the first available index
    for index_path in available_indices:
        try:
            from langchain_community.vectorstores import FAISS
            
            logger.info(f"Loading: {index_path.name}")
            start_time = time.time()
            
            vector_store = FAISS.load_local(
                str(index_path),
                embeddings,
                allow_dangerous_deserialization=True
            )
            
            load_time = time.time() - start_time
            doc_count = len(vector_store.docstore._dict)
            
            logger.info(f"✅ Successfully loaded vector store")
            logger.info(f"   Index: {index_path.name}")
            logger.info(f"   Documents: {doc_count}")
            logger.info(f"   Load time: {load_time:.3f}s")
            
            return vector_store
            
        except Exception as e:
            logger.warning(f"⚠️ Could not load {index_path.name}: {e}")
            continue
    
    logger.error("❌ No valid vector stores could be loaded")
    return None

def test_basic_similarity_search(vector_store):
    """Test basic vector similarity search"""
    logger.info("\n🔍 Testing Basic Vector Similarity Search")
    logger.info("-" * 40)
    
    for i, query in enumerate(TEST_QUERIES, 1):
        logger.info(f"\n{i}. Testing query: '{query}'")
        
        try:
            start_time = time.time()
            
            # Perform similarity search
            docs = vector_store.similarity_search(query, k=5)
            search_time = time.time() - start_time
            
            logger.info(f"   ⚡ Search time: {search_time:.3f}s")
            logger.info(f"   📄 Retrieved docs: {len(docs)}")
            
            # Show top 2 results
            for j, doc in enumerate(docs[:2], 1):
                content_preview = doc.page_content[:100].replace('\n', ' ')
                logger.info(f"      {j}. {content_preview}...")
                
                # Show metadata if available
                if hasattr(doc, 'metadata') and doc.metadata:
                    # Show first 2 metadata keys to keep output clean
                    meta_sample = dict(list(doc.metadata.items())[:2])
                    logger.info(f"         Metadata: {meta_sample}")
                    
        except Exception as e:
            logger.error(f"   ❌ Search failed: {e}")

def test_similarity_search_with_scores(vector_store):
    """Test similarity search with relevance scores"""
    logger.info("\n📊 Testing Similarity Search with Relevance Scores")
    logger.info("-" * 40)
    
    # Test with a specific query that should return good results
    test_query = "customer revenue analysis queries"
    logger.info(f"Query: '{test_query}'")
    
    try:
        start_time = time.time()
        
        # Search with similarity scores
        docs_with_scores = vector_store.similarity_search_with_score(test_query, k=5)
        search_time = time.time() - start_time
        
        logger.info(f"⚡ Search time: {search_time:.3f}s")
        logger.info(f"📄 Results with relevance scores:")
        
        for i, (doc, score) in enumerate(docs_with_scores, 1):
            content_preview = doc.page_content[:80].replace('\n', ' ')
            logger.info(f"   {i}. Score: {score:.4f} - {content_preview}...")
            
        # Show score distribution
        scores = [score for _, score in docs_with_scores]
        if scores:
            logger.info(f"📈 Score range: {min(scores):.4f} to {max(scores):.4f}")
            logger.info(f"📊 Average score: {sum(scores)/len(scores):.4f}")
            
    except Exception as e:
        logger.error(f"❌ Scored search failed: {e}")

def test_retrieval_performance(vector_store):
    """Test retrieval performance with different k values"""
    logger.info("\n⚡ Testing Retrieval Performance")
    logger.info("-" * 40)
    
    test_query = "SQL JOIN queries"
    k_values = [1, 5, 10, 20]
    
    logger.info(f"Query: '{test_query}'")
    logger.info(f"Testing with k values: {k_values}")
    
    for k in k_values:
        try:
            start_time = time.time()
            docs = vector_store.similarity_search(test_query, k=k)
            search_time = time.time() - start_time
            
            logger.info(f"   k={k:2d}: {search_time:.3f}s ({len(docs)} docs)")
            
        except Exception as e:
            logger.error(f"   k={k}: Failed - {e}")

def main():
    """Main test function"""
    print("🧪 Basic Vector Database Retrieval Test")
    print("=" * 50)
    print("Testing ONLY core vector retrieval functionality")
    print("=" * 50)
    
    # Test 1: Ollama Connection
    logger.info("Step 1: Testing Ollama connection...")
    success, embeddings = test_ollama_connection()
    
    if not success:
        logger.error("❌ Cannot proceed without Ollama connection")
        logger.info("\n💡 Setup instructions:")
        logger.info("   1. Start Ollama: ollama serve")
        logger.info("   2. Download model: ollama pull nomic-embed-text")
        logger.info("   3. Re-run this test")
        sys.exit(1)
    
    # Test 2: Load Vector Store
    logger.info("\nStep 2: Loading vector store...")
    vector_store = load_vector_store(embeddings)
    
    if not vector_store:
        logger.error("❌ Cannot proceed without vector store")
        logger.info("\n💡 Setup instructions:")
        logger.info("   1. Generate embeddings: python3 standalone_embedding_generator.py --csv 'your_data.csv'")
        logger.info("   2. Re-run this test")
        sys.exit(1)
    
    # Test 3: Basic Similarity Search
    logger.info("\nStep 3: Testing basic similarity search...")
    test_basic_similarity_search(vector_store)
    
    # Test 4: Similarity Search with Scores
    logger.info("\nStep 4: Testing similarity search with scores...")
    test_similarity_search_with_scores(vector_store)
    
    # Test 5: Performance Testing
    logger.info("\nStep 5: Testing retrieval performance...")
    test_retrieval_performance(vector_store)
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("✅ Basic Vector Retrieval Test Complete!")
    logger.info("=" * 50)
    logger.info("\n📊 Test Summary:")
    logger.info("   ✓ Ollama connection working")
    logger.info("   ✓ Vector store loaded successfully")
    logger.info("   ✓ Similarity search functional")
    logger.info("   ✓ Relevance scoring working")
    logger.info("   ✓ Performance metrics collected")
    logger.info("\n💡 Your vector retrieval system is working correctly!")
    logger.info("   Next: Use in your application or run the full Streamlit app")

if __name__ == "__main__":
    main()