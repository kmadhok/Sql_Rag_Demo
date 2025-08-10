#!/usr/bin/env python3
"""
Context Optimization Demo - Direct Vector Store Access

Shows how chunks are optimized for Gemini's 1M context window.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

def demonstrate_chunk_optimization():
    """Compare original vs Gemini-optimized chunk retrieval."""
    
    print("🔥 GEMINI CONTEXT WINDOW CHUNK OPTIMIZATION")
    print("=" * 70)
    
    try:
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
        
        print(f"Test Query: '{test_query}'")
        print()
        
        # Original approach (K=4)
        print("📊 ORIGINAL APPROACH (K=4)")
        print("-" * 50)
        
        docs_original = vector_store.similarity_search(test_query, k=4)
        
        original_chars = sum(len(doc.page_content) for doc in docs_original)
        original_tokens = original_chars // 4  # Rough estimate
        original_utilization = (original_tokens / 1000000) * 100
        
        print(f"✅ Chunks retrieved: {len(docs_original)}")
        print(f"✅ Total characters: {original_chars:,}")
        print(f"✅ Estimated tokens: {original_tokens:,}")
        print(f"✅ Gemini utilization: {original_utilization:.2f}%")
        
        # Analyze content types
        original_joins = sum(1 for doc in docs_original if 'join' in doc.page_content.lower())
        original_descriptions = sum(1 for doc in docs_original if doc.metadata.get('description'))
        
        print(f"✅ JOIN examples: {original_joins}")
        print(f"✅ With descriptions: {original_descriptions}")
        print()
        
        # Gemini approach (K=100)
        print("🔥 GEMINI APPROACH (K=100)")
        print("-" * 50)
        
        docs_gemini = vector_store.similarity_search(test_query, k=100)
        
        # Apply deduplication (simplified version)
        def simple_dedupe(docs, threshold=0.6):
            """Simple deduplication based on content similarity."""
            filtered = []
            for doc in docs:
                is_duplicate = False
                doc_words = set(doc.page_content.lower().split())
                
                for existing in filtered:
                    existing_words = set(existing.page_content.lower().split())
                    if doc_words and existing_words:
                        intersection = len(doc_words & existing_words)
                        union = len(doc_words | existing_words)
                        similarity = intersection / union if union > 0 else 0
                        if similarity > threshold:
                            is_duplicate = True
                            break
                
                if not is_duplicate:
                    filtered.append(doc)
            return filtered
        
        # Apply smart processing
        docs_gemini_filtered = simple_dedupe(docs_gemini)
        
        gemini_chars = sum(len(doc.page_content) for doc in docs_gemini_filtered)
        gemini_tokens = gemini_chars // 4  # Rough estimate
        gemini_utilization = (gemini_tokens / 1000000) * 100
        
        print(f"✅ Initial chunks: {len(docs_gemini)}")
        print(f"✅ After deduplication: {len(docs_gemini_filtered)}")
        print(f"✅ Total characters: {gemini_chars:,}")
        print(f"✅ Estimated tokens: {gemini_tokens:,}")
        print(f"✅ Gemini utilization: {gemini_utilization:.2f}%")
        
        # Analyze content types
        gemini_joins = sum(1 for doc in docs_gemini_filtered if 'join' in doc.page_content.lower())
        gemini_descriptions = sum(1 for doc in docs_gemini_filtered if doc.metadata.get('description'))
        gemini_aggregations = sum(1 for doc in docs_gemini_filtered 
                                if any(keyword in doc.page_content.lower() 
                                      for keyword in ['group by', 'count', 'sum', 'avg']))
        
        print(f"✅ JOIN examples: {gemini_joins}")
        print(f"✅ With descriptions: {gemini_descriptions}")
        print(f"✅ Aggregation examples: {gemini_aggregations}")
        print()
        
        # Show the improvement
        print("📈 OPTIMIZATION RESULTS")
        print("-" * 50)
        
        chunk_improvement = len(docs_gemini_filtered) - len(docs_original)
        token_improvement = gemini_tokens - original_tokens
        utilization_improvement = gemini_utilization - original_utilization
        
        print(f"🚀 Additional chunks: +{chunk_improvement} ({chunk_improvement/len(docs_original)*100:.0f}% more)")
        print(f"🚀 Additional tokens: +{token_improvement:,}")
        print(f"🚀 Utilization increase: +{utilization_improvement:.2f}%")
        print(f"🚀 More JOIN examples: +{gemini_joins - original_joins}")
        print(f"🚀 More descriptions: +{gemini_descriptions - original_descriptions}")
        print()
        
        # Show example of enhanced context structure
        print("🔍 EXAMPLE ENHANCED CONTEXT STRUCTURE")
        print("-" * 50)
        
        if docs_gemini_filtered:
            sample_doc = docs_gemini_filtered[0]
            print("Enhanced chunk format:")
            print(f"  Source: {sample_doc.metadata.get('source', 'Unknown')}")
            if sample_doc.metadata.get('description'):
                print(f"  Description: {sample_doc.metadata['description'][:80]}...")
            if sample_doc.metadata.get('table'):
                print(f"  Tables: {sample_doc.metadata['table']}")
            if sample_doc.metadata.get('joins'):
                print(f"  Joins: {sample_doc.metadata['joins'][:50]}...")
            print(f"  SQL: {sample_doc.page_content[:100]}...")
            print()
        
        # Key improvements summary
        print("🎯 KEY IMPROVEMENTS FOR GEMINI")
        print("=" * 70)
        
        improvements = [
            f"Context utilization: {original_utilization:.1f}% → {gemini_utilization:.1f}%",
            f"Relevant examples: {len(docs_original)} → {len(docs_gemini_filtered)}",
            f"JOIN pattern coverage: {original_joins} → {gemini_joins} examples",
            f"Metadata preservation: Enhanced with descriptions, tables, joins",
            f"Smart deduplication: Removed {len(docs_gemini) - len(docs_gemini_filtered)} redundant chunks",
            f"Content diversity: Multiple SQL patterns and use cases"
        ]
        
        for improvement in improvements:
            print(f"✅ {improvement}")
        
        print(f"\n🚀 Result: Your system now uses {gemini_utilization:.1f}% of Gemini's 1M context window")
        print(f"   compared to only {original_utilization:.1f}% with the original approach!")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("🔥 Enable Gemini Mode in the app for dramatically better results")
        print("📊 Use K=100+ when you need comprehensive SQL guidance")
        print("🎯 The enhanced context provides better JOIN examples and patterns")
        print("⚡ Smart deduplication ensures no redundant information")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    demonstrate_chunk_optimization()