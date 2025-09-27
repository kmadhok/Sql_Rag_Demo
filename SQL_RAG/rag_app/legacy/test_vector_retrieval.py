#!/usr/bin/env python3
"""
Vector Database Retrieval Test Script

Tests the complete vector retrieval pipeline including:
- Vector store loading
- Embedding generation
- Similarity search
- Hybrid search (if available)
- Query rewriting
- Schema injection

Usage:
    python3 test_vector_retrieval.py
"""

import logging
import time
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test queries for different scenarios
TEST_QUERIES = [
    {
        "query": "How to calculate customer lifetime value?",
        "description": "Business analytics query",
        "expected_type": "conceptual"
    },
    {
        "query": "Show me JOIN queries with customers table",
        "description": "Table-specific SQL query", 
        "expected_type": "table_specific"
    },
    {
        "query": "GROUP BY and COUNT examples",
        "description": "SQL function query",
        "expected_type": "sql_functions"
    },
    {
        "query": "inventory management reports",
        "description": "Domain-specific query",
        "expected_type": "domain"
    },
    {
        "query": "@schema show tables with customer data",
        "description": "Schema exploration",
        "expected_type": "schema"
    }
]

def test_ollama_connection():
    """Test Ollama service connection"""
    logger.info("🔧 Testing Ollama Connection")
    logger.info("-" * 40)
    
    try:
        from langchain_ollama import OllamaEmbeddings
        
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        # Test embedding generation
        test_text = "This is a test query for embedding generation"
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
    """Load existing vector store"""
    logger.info("\n📁 Loading Vector Store")
    logger.info("-" * 40)
    
    # Look for vector stores
    indices_dir = Path("faiss_indices")
    
    if not indices_dir.exists():
        logger.error("❌ No faiss_indices directory found")
        logger.info("💡 Run: python3 standalone_embedding_generator.py --csv 'your_data.csv'")
        return None
    
    # Find available indices
    available_indices = list(indices_dir.glob("index_*"))
    
    if not available_indices:
        logger.error("❌ No vector indices found in faiss_indices/")
        return None
    
    # Load the first available index
    for index_path in available_indices:
        try:
            from langchain_community.vectorstores import FAISS
            
            start_time = time.time()
            vector_store = FAISS.load_local(
                str(index_path),
                embeddings,
                allow_dangerous_deserialization=True
            )
            load_time = time.time() - start_time
            
            doc_count = len(vector_store.docstore._dict)
            
            logger.info(f"✅ Loaded vector store: {index_path.name}")
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
    logger.info("\n🔍 Testing Basic Similarity Search")
    logger.info("-" * 40)
    
    for i, test_case in enumerate(TEST_QUERIES[:3], 1):
        query = test_case["query"]
        description = test_case["description"]
        
        logger.info(f"\n{i}. Query: '{query}'")
        logger.info(f"   Type: {description}")
        
        try:
            start_time = time.time()
            
            # Basic similarity search
            docs = vector_store.similarity_search(query, k=5)
            search_time = time.time() - start_time
            
            logger.info(f"   ⚡ Search time: {search_time:.3f}s")
            logger.info(f"   📄 Retrieved docs: {len(docs)}")
            
            # Show top results
            for j, doc in enumerate(docs[:2]):
                content_preview = doc.page_content[:100].replace('\n', ' ')
                logger.info(f"      {j+1}. {content_preview}...")
                if hasattr(doc, 'metadata') and doc.metadata:
                    logger.info(f"         Metadata: {dict(list(doc.metadata.items())[:2])}")
                    
        except Exception as e:
            logger.error(f"   ❌ Search failed: {e}")

def test_similarity_search_with_scores(vector_store):
    """Test similarity search with relevance scores"""
    logger.info("\n📊 Testing Similarity Search with Scores")
    logger.info("-" * 40)
    
    query = "customer revenue analysis queries"
    logger.info(f"Query: '{query}'")
    
    try:
        start_time = time.time()
        
        # Search with similarity scores
        docs_with_scores = vector_store.similarity_search_with_score(query, k=5)
        search_time = time.time() - start_time
        
        logger.info(f"⚡ Search time: {search_time:.3f}s")
        logger.info(f"📄 Results with scores:")
        
        for i, (doc, score) in enumerate(docs_with_scores, 1):
            content_preview = doc.page_content[:80].replace('\n', ' ')
            logger.info(f"   {i}. Score: {score:.4f} - {content_preview}...")
            
    except Exception as e:
        logger.error(f"❌ Scored search failed: {e}")

def test_hybrid_search(vector_store):
    """Test hybrid search if available"""
    logger.info("\n🔀 Testing Hybrid Search")
    logger.info("-" * 40)
    
    try:
        from hybrid_retriever import HybridRetriever
        
        # Initialize hybrid retriever
        hybrid_retriever = HybridRetriever(
            vector_store=vector_store,
            auto_adjust_weights=True
        )
        
        query = "JOIN customers and orders tables"
        logger.info(f"Query: '{query}'")
        
        start_time = time.time()
        
        # Hybrid search
        hybrid_result = hybrid_retriever.retrieve(query, k=5)
        search_time = time.time() - start_time
        
        logger.info(f"⚡ Hybrid search time: {search_time:.3f}s")
        logger.info(f"📄 Retrieved docs: {len(hybrid_result.documents)}")
        logger.info(f"⚖️ Used weights - Vector: {hybrid_result.weights_used.vector_weight:.2f}, Keyword: {hybrid_result.weights_used.keyword_weight:.2f}")
        
        # Show breakdown if available
        if hasattr(hybrid_result, 'retrieval_breakdown'):
            breakdown = hybrid_result.retrieval_breakdown
            logger.info(f"📊 Retrieval breakdown:")
            for method, count in breakdown.items():
                logger.info(f"   {method}: {count} docs")
        
        # Show top results
        for i, doc in enumerate(hybrid_result.documents[:2], 1):
            content_preview = doc.page_content[:80].replace('\n', ' ')
            logger.info(f"   {i}. {content_preview}...")
            
    except ImportError:
        logger.warning("⚠️ Hybrid search not available")
        logger.info("💡 Install: pip install rank-bm25")
    except Exception as e:
        logger.error(f"❌ Hybrid search failed: {e}")

def test_query_rewriting():
    """Test query rewriting functionality"""
    logger.info("\n✍️ Testing Query Rewriting")
    logger.info("-" * 40)
    
    try:
        from simple_query_rewriter import SimpleQueryRewriter
        
        rewriter = SimpleQueryRewriter()
        
        # Test query rewriting
        test_queries = [
            "show customer data",
            "calculate revenue totals", 
            "inventory levels"
        ]
        
        for query in test_queries:
            logger.info(f"\nOriginal: '{query}'")
            
            start_time = time.time()
            result = rewriter.rewrite_query(query)
            rewrite_time = time.time() - start_time
            
            logger.info(f"Enhanced: '{result['rewritten_query']}'")
            logger.info(f"Changed: {result['query_changed']}")
            logger.info(f"Method: {result['method']}")
            logger.info(f"Time: {rewrite_time:.3f}s")
            
            if result['error']:
                logger.warning(f"Error: {result['error']}")
                
    except ImportError:
        logger.warning("⚠️ Query rewriting not available")
    except Exception as e:
        logger.error(f"❌ Query rewriting failed: {e}")

def test_full_rag_pipeline():
    """Test the complete RAG pipeline"""
    logger.info("\n🚀 Testing Complete RAG Pipeline")
    logger.info("-" * 40)
    
    try:
        from simple_rag_simple_gemini import answer_question_simple_gemini
        
        # Load vector store for RAG
        embeddings = None
        try:
            from langchain_ollama import OllamaEmbeddings
            embeddings = OllamaEmbeddings(model="nomic-embed-text")
        except:
            logger.error("❌ Could not initialize embeddings")
            return
        
        vector_store = load_vector_store(embeddings)
        if not vector_store:
            logger.error("❌ Could not load vector store")
            return
        
        # Test RAG query
        test_query = "How do I calculate customer lifetime value using SQL?"
        logger.info(f"RAG Query: '{test_query}'")
        
        start_time = time.time()
        
        # Run complete RAG pipeline
        result = answer_question_simple_gemini(
            question=test_query,
            vector_store=vector_store,
            k=10,
            gemini_mode=True,
            hybrid_search=True,
            enable_query_rewriting=True
        )
        
        total_time = time.time() - start_time
        
        if result:
            answer, retrieved_docs, usage_info = result
            
            logger.info(f"⚡ Total pipeline time: {total_time:.3f}s")
            logger.info(f"📄 Retrieved documents: {len(retrieved_docs)}")
            logger.info(f"💬 Answer length: {len(answer)} chars")
            
            # Show usage info
            if usage_info:
                logger.info(f"📊 Usage info:")
                for key, value in usage_info.items():
                    if isinstance(value, dict):
                        logger.info(f"   {key}: {value}")
                    else:
                        logger.info(f"   {key}: {value}")
            
            # Show answer preview
            answer_preview = answer[:200].replace('\n', ' ')
            logger.info(f"📝 Answer preview: {answer_preview}...")
            
        else:
            logger.error("❌ RAG pipeline returned no result")
            
    except ImportError as e:
        logger.error(f"❌ RAG imports failed: {e}")
    except Exception as e:
        logger.error(f"❌ RAG pipeline failed: {e}")

def main():
    """Main test function"""
    print("🧪 Vector Database Retrieval Test")
    print("=" * 50)
    
    # Test Ollama connection
    success, embeddings = test_ollama_connection()
    if not success:
        logger.error("❌ Cannot proceed without Ollama")
        sys.exit(1)
    
    # Load vector store
    vector_store = load_vector_store(embeddings)
    if not vector_store:
        logger.error("❌ Cannot proceed without vector store")
        sys.exit(1)
    
    # Run tests
    test_basic_similarity_search(vector_store)
    test_similarity_search_with_scores(vector_store)
    test_hybrid_search(vector_store)
    test_query_rewriting()
    test_full_rag_pipeline()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("✅ Vector Retrieval Test Complete!")
    logger.info("=" * 50)
    logger.info("\n💡 Next steps:")
    logger.info("   1. Run the Streamlit app: streamlit run app_simple_gemini.py")
    logger.info("   2. Try the Query Search tab with different options")
    logger.info("   3. Test with your own queries in the Chat interface")

if __name__ == "__main__":
    main()