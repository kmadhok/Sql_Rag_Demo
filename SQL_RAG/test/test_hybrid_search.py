#!/usr/bin/env python3
"""
Test script for hybrid search implementation

This script tests the hybrid search functionality with sample queries
to validate the implementation and demonstrate improvements.
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Any

# Import our hybrid search components
from hybrid_retriever import HybridRetriever, SQLQueryAnalyzer, SearchWeights
from simple_rag_simple_gemini import answer_question_simple_gemini, test_ollama_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test queries that should benefit from hybrid search
TEST_QUERIES = [
    {
        "query": "How to join customers and orders tables?",
        "expected_benefits": "Should find exact table name matches + semantic JOIN patterns",
        "type": "table_specific"
    },
    {
        "query": "Show me queries with GROUP BY and COUNT functions",
        "expected_benefits": "Should match exact SQL keywords + aggregation concepts",
        "type": "sql_functions"
    },
    {
        "query": "What's the best way to calculate customer revenue?",
        "expected_benefits": "Should find semantic revenue concepts + calculation patterns",
        "type": "conceptual"
    },
    {
        "query": "inventory management queries",
        "expected_benefits": "Should match inventory table + management concepts",
        "type": "domain_specific"
    },
    {
        "query": "SELECT statements with INNER JOIN",
        "expected_benefits": "Should match exact SQL syntax + join patterns",
        "type": "syntax_specific"
    }
]

def load_test_vector_store():
    """Load vector store for testing"""
    try:
        from langchain_ollama import OllamaEmbeddings
        from langchain_community.vectorstores import FAISS
        
        # Look for existing vector stores
        indices_dir = Path(__file__).parent / "faiss_indices"
        
        if not indices_dir.exists():
            logger.error("❌ No faiss_indices directory found")
            return None
        
        # Find the first available index
        for index_dir in indices_dir.glob("index_*"):
            if index_dir.is_dir():
                try:
                    embeddings = OllamaEmbeddings(model="nomic-embed-text")
                    vector_store = FAISS.load_local(
                        str(index_dir),
                        embeddings,
                        allow_dangerous_deserialization=True
                    )
                    logger.info(f"✅ Loaded vector store from {index_dir}")
                    return vector_store
                except Exception as e:
                    logger.warning(f"Could not load {index_dir}: {e}")
                    continue
        
        logger.error("❌ No valid vector stores found")
        return None
        
    except Exception as e:
        logger.error(f"Error loading vector store: {e}")
        return None

def test_query_analysis():
    """Test the SQL query analyzer"""
    logger.info("\n" + "="*60)
    logger.info("🔍 Testing SQL Query Analysis")
    logger.info("="*60)
    
    analyzer = SQLQueryAnalyzer()
    
    for test_case in TEST_QUERIES:
        query = test_case["query"]
        logger.info(f"\n📝 Query: '{query}'")
        
        analysis = analyzer.analyze_query_type(query)
        recommended_weights = analysis['recommended_weights']
        
        logger.info(f"   📊 Analysis Results:")
        logger.info(f"      - Has table names: {analysis['has_table_names']}")
        logger.info(f"      - Has SQL functions: {analysis['has_sql_functions']}")
        logger.info(f"      - Has joins: {analysis['has_joins']}")
        logger.info(f"      - Technical terms count: {analysis['has_technical_terms']}")
        logger.info(f"      - Is schema query: {analysis['is_schema_query']}")
        logger.info(f"   🎛️ Recommended weights:")
        logger.info(f"      - Vector: {recommended_weights.vector_weight:.2f}")
        logger.info(f"      - Keyword: {recommended_weights.keyword_weight:.2f}")
        logger.info(f"   💡 Expected: {test_case['expected_benefits']}")

def test_hybrid_search_comparison(vector_store):
    """Test hybrid search vs vector-only search"""
    logger.info("\n" + "="*60)
    logger.info("🔀 Testing Hybrid vs Vector Search")
    logger.info("="*60)
    
    # Test first 3 queries
    for i, test_case in enumerate(TEST_QUERIES[:3]):
        query = test_case["query"]
        logger.info(f"\n🧪 Test {i+1}: '{query}'")
        
        try:
            # Vector-only search
            start_time = time.time()
            vector_result = answer_question_simple_gemini(
                question=query,
                vector_store=vector_store,
                k=5,
                gemini_mode=False,
                hybrid_search=False
            )
            vector_time = time.time() - start_time
            
            # Hybrid search
            start_time = time.time()
            hybrid_result = answer_question_simple_gemini(
                question=query,
                vector_store=vector_store,
                k=5,
                gemini_mode=False,
                hybrid_search=True,
                auto_adjust_weights=True
            )
            hybrid_time = time.time() - start_time
            
            logger.info(f"   ⚡ Performance:")
            logger.info(f"      - Vector-only: {vector_time:.2f}s")
            logger.info(f"      - Hybrid: {hybrid_time:.2f}s")
            
            if vector_result and hybrid_result:
                vector_answer, vector_docs, vector_usage = vector_result
                hybrid_answer, hybrid_docs, hybrid_usage = hybrid_result
                
                logger.info(f"   📊 Results:")
                logger.info(f"      - Vector docs: {len(vector_docs)}")
                logger.info(f"      - Hybrid docs: {len(hybrid_docs)}")
                
                # Check for hybrid search breakdown
                if hybrid_usage.get('hybrid_search_breakdown'):
                    breakdown = hybrid_usage['hybrid_search_breakdown']
                    logger.info(f"   🔀 Hybrid breakdown:")
                    logger.info(f"      - Hybrid matches: {breakdown.get('hybrid', 0)}")
                    logger.info(f"      - Vector only: {breakdown.get('vector', 0)}")
                    logger.info(f"      - Keyword only: {breakdown.get('keyword', 0)}")
                
                # Compare answer quality (basic metrics)
                vector_length = len(vector_answer) if vector_answer else 0
                hybrid_length = len(hybrid_answer) if hybrid_answer else 0
                
                logger.info(f"   📝 Answer comparison:")
                logger.info(f"      - Vector answer length: {vector_length}")
                logger.info(f"      - Hybrid answer length: {hybrid_length}")
                
            else:
                logger.warning(f"   ⚠️ Some results failed to generate")
                
        except Exception as e:
            logger.error(f"   ❌ Test failed: {e}")

def test_weight_adjustment():
    """Test automatic weight adjustment for different query types"""
    logger.info("\n" + "="*60)
    logger.info("🎛️ Testing Weight Adjustment")
    logger.info("="*60)
    
    analyzer = SQLQueryAnalyzer()
    
    # Test queries with different characteristics
    weight_test_queries = [
        ("customer revenue analysis", "conceptual - should favor vector"),
        ("SELECT * FROM customers WHERE id = 1", "exact SQL - should favor keyword"),
        ("table schema information", "schema query - should favor keyword"),
        ("GROUP BY COUNT SUM", "heavy SQL functions - should favor keyword"),
        ("best practices for data analysis", "general concept - should favor vector")
    ]
    
    for query, description in weight_test_queries:
        logger.info(f"\n📝 Query: '{query}'")
        logger.info(f"   🎯 Expected: {description}")
        
        analysis = analyzer.analyze_query_type(query)
        weights = analysis['recommended_weights']
        
        # Determine primary method
        if weights.vector_weight > weights.keyword_weight:
            primary = "vector"
            ratio = weights.vector_weight / weights.keyword_weight
        else:
            primary = "keyword"
            ratio = weights.keyword_weight / weights.vector_weight
        
        logger.info(f"   ⚖️ Weights: Vector {weights.vector_weight:.2f}, Keyword {weights.keyword_weight:.2f}")
        logger.info(f"   🎯 Primary method: {primary} (ratio: {ratio:.1f}:1)")

def main():
    """Main test function"""
    logger.info("🧪 Hybrid Search Implementation Test")
    logger.info("="*60)
    
    # Test Ollama connection first
    logger.info("1. Testing Ollama connection...")
    success, message = test_ollama_connection()
    logger.info(f"   {message}")
    
    if not success:
        logger.error("❌ Cannot proceed without Ollama. Please start the service.")
        return
    
    # Test query analysis
    test_query_analysis()
    
    # Test weight adjustment
    test_weight_adjustment()
    
    # Load vector store for full tests
    logger.info("\n2. Loading vector store...")
    vector_store = load_test_vector_store()
    
    if vector_store:
        logger.info(f"   ✅ Vector store loaded with {len(vector_store.docstore._dict)} documents")
        
        # Test hybrid vs vector search
        test_hybrid_search_comparison(vector_store)
        
        logger.info("\n" + "="*60)
        logger.info("✅ Hybrid Search Implementation Test Complete!")
        logger.info("="*60)
        logger.info("\n💡 Next steps:")
        logger.info("   1. Run: streamlit run app_simple_gemini.py")
        logger.info("   2. Enable 🔀 Hybrid Search in the sidebar")
        logger.info("   3. Try different query types to see the benefits")
        logger.info("   4. Compare results with hybrid search on/off")
        
    else:
        logger.error("❌ Could not load vector store. Please run standalone_embedding_generator.py first.")
        logger.info("💡 Run: python standalone_embedding_generator.py --csv 'your_data.csv'")

if __name__ == "__main__":
    main()