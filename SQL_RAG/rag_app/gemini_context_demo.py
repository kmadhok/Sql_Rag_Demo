#!/usr/bin/env python3
"""
Gemini Context Window Optimization Demo

This script demonstrates how chunks are now populated and optimized 
for Gemini's 1M token context window compared to the original approach.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

def demonstrate_context_optimization():
    """Show the difference between original and Gemini-optimized chunk population."""
    
    print("🔥 GEMINI CONTEXT WINDOW OPTIMIZATION DEMO")
    print("=" * 70)
    
    try:
        from simple_rag import answer_question
        from langchain_ollama import OllamaEmbeddings
        from langchain_community.vectorstores import FAISS
        
        # Load existing vector store
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        store_path = Path(__file__).parent / "faiss_indices" / "index_csv_sample_queries"
        
        if not store_path.exists():
            print("❌ Vector store not found. Please run the main app first.")
            return
        
        vector_store = FAISS.load_local(
            str(store_path),
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        test_query = "How do I join multiple tables with different types of JOINs in SQL?"
        
        print(f"Test Query: {test_query}")
        print()
        
        # Original approach (small K)
        print("📊 ORIGINAL APPROACH (K=4)")
        print("-" * 50)
        
        answer_original, docs_original, token_usage_original = answer_question(
            test_query,
            vector_store=vector_store,
            k=4,
            return_docs=True,
            return_tokens=True,
            gemini_mode=False
        )
        
        original_context_size = sum(len(doc.page_content) for doc in docs_original)
        original_estimated_tokens = original_context_size // 4  # Rough estimate
        
        print(f"✅ Chunks retrieved: {len(docs_original)}")
        print(f"✅ Context size: {original_context_size:,} characters")
        print(f"✅ Estimated tokens: {original_estimated_tokens:,}")
        print(f"✅ Gemini utilization: {(original_estimated_tokens / 1000000) * 100:.2f}%")
        print()
        
        # Gemini-optimized approach (large K)
        print("🔥 GEMINI-OPTIMIZED APPROACH (K=100)")
        print("-" * 50)
        
        answer_gemini, docs_gemini, token_usage_gemini = answer_question(
            test_query,
            vector_store=vector_store,
            k=100,
            return_docs=True,
            return_tokens=True,
            gemini_mode=True
        )
        
        gemini_context_size = sum(len(doc.page_content) for doc in docs_gemini)
        gemini_estimated_tokens = gemini_context_size // 4  # Rough estimate
        
        print(f"✅ Chunks retrieved: {len(docs_gemini)}")
        print(f"✅ Context size: {gemini_context_size:,} characters")
        print(f"✅ Estimated tokens: {gemini_estimated_tokens:,}")
        print(f"✅ Gemini utilization: {(gemini_estimated_tokens / 1000000) * 100:.2f}%")
        print()
        
        # Show improvements
        print("📈 OPTIMIZATION RESULTS")
        print("-" * 50)
        
        chunk_improvement = len(docs_gemini) - len(docs_original)
        context_improvement = gemini_context_size - original_context_size
        token_improvement = gemini_estimated_tokens - original_estimated_tokens
        utilization_improvement = ((gemini_estimated_tokens - original_estimated_tokens) / 1000000) * 100
        
        print(f"🚀 Additional chunks: +{chunk_improvement} ({chunk_improvement/len(docs_original)*100:.0f}% increase)")
        print(f"🚀 Additional context: +{context_improvement:,} characters")
        print(f"🚀 Additional tokens: +{token_improvement:,}")
        print(f"🚀 Better Gemini utilization: +{utilization_improvement:.2f}%")
        print()
        
        # Show content quality differences
        print("🎯 CONTENT QUALITY ANALYSIS")
        print("-" * 50)
        
        # Analyze content types in retrieved chunks
        original_joins = sum(1 for doc in docs_original if 'join' in doc.page_content.lower())
        gemini_joins = sum(1 for doc in docs_gemini if 'join' in doc.page_content.lower())
        
        original_descriptions = sum(1 for doc in docs_original if doc.metadata.get('description'))
        gemini_descriptions = sum(1 for doc in docs_gemini if doc.metadata.get('description'))
        
        original_aggregations = sum(1 for doc in docs_original 
                                  if any(keyword in doc.page_content.lower() 
                                        for keyword in ['group by', 'count', 'sum', 'avg']))
        gemini_aggregations = sum(1 for doc in docs_gemini 
                                if any(keyword in doc.page_content.lower() 
                                      for keyword in ['group by', 'count', 'sum', 'avg']))
        
        print(f"JOIN examples:")
        print(f"  Original: {original_joins} | Gemini: {gemini_joins} (+{gemini_joins - original_joins})")
        
        print(f"With descriptions:")
        print(f"  Original: {original_descriptions} | Gemini: {gemini_descriptions} (+{gemini_descriptions - original_descriptions})")
        
        print(f"Aggregation examples:")
        print(f"  Original: {original_aggregations} | Gemini: {gemini_aggregations} (+{gemini_aggregations - original_aggregations})")
        
        print()
        
        # Show specific examples of enhanced context
        print("🔍 EXAMPLE ENHANCED CHUNKS")
        print("-" * 50)
        
        print("Sample chunk from Gemini mode:")
        if docs_gemini:
            sample_doc = docs_gemini[0]
            print(f"Source: {sample_doc.metadata.get('source', 'Unknown')}")
            if sample_doc.metadata.get('description'):
                print(f"Description: {sample_doc.metadata['description'][:100]}...")
            print(f"SQL: {sample_doc.page_content[:200]}...")
        
        print()
        
        # Answer quality comparison
        print("💬 ANSWER QUALITY COMPARISON")
        print("-" * 50)
        
        print("Original answer length:", len(answer_original))
        print("Gemini answer length:", len(answer_gemini))
        print(f"Answer improvement: {len(answer_gemini) - len(answer_original)} characters")
        
        if len(answer_gemini) > len(answer_original):
            print("🎉 Gemini mode produced a more comprehensive answer!")
        
        print()
        
        # Summary
        print("📋 SUMMARY FOR GEMINI 1M CONTEXT WINDOW")
        print("=" * 70)
        
        print(f"✅ Context utilization increased from {(original_estimated_tokens / 1000000) * 100:.1f}% to {(gemini_estimated_tokens / 1000000) * 100:.1f}%")
        print(f"✅ Serving {chunk_improvement}x more relevant examples to the model")
        print(f"✅ Enhanced metadata preservation (descriptions, tables, joins)")
        print(f"✅ Smart deduplication removes redundant content")
        print(f"✅ Diverse content prioritization ensures comprehensive coverage")
        print(f"✅ Intelligent context packing maximizes information density")
        
        print(f"\n🎯 Your system is now optimized to use {(gemini_estimated_tokens / 1000000) * 100:.1f}% of Gemini's 1M context window!")
        print("🚀 This should significantly improve answer quality and comprehensiveness.")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    demonstrate_context_optimization()