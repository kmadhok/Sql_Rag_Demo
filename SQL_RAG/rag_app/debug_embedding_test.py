#!/usr/bin/env python3
"""
Debug script to test embedding creation outside of Streamlit.
This helps isolate the issue and see exactly where it's hanging.
"""

import sys
import time
import pandas as pd
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def test_csv_loading():
    """Test loading the CSV file."""
    print("🧪 Testing CSV loading...")
    csv_path = '/Users/kanumadhok/Sql_Rag_Demo/SQL_RAG/sample_test.csv'
    
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ Loaded CSV with {len(df)} rows")
        print(f"✅ Columns: {list(df.columns)}")
        
        if 'query' in df.columns:
            non_empty = df['query'].notna().sum()
            print(f"✅ Non-empty queries: {non_empty}")
            
            # Show first few queries
            print("\n🔍 First 3 queries:")
            for i, query in enumerate(df['query'].head(3)):
                if pd.notna(query):
                    print(f"  {i+1}: {str(query)[:100]}...")
        else:
            print("❌ No 'query' column found!")
            
        return df
        
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return None

def test_ollama_availability():
    """Test Ollama service availability."""
    print("\n🧪 Testing Ollama availability...")
    
    try:
        from actions.ollama_llm_client import check_ollama_availability
        available, message = check_ollama_availability()
        
        if available:
            print(f"✅ Ollama available: {message}")
        else:
            print(f"❌ Ollama not available: {message}")
        
        return available
        
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False

def test_embedding_manager():
    """Test the EmbeddingManager directly."""
    print("\n🧪 Testing EmbeddingManager...")
    
    try:
        from actions.embedding_manager import EmbeddingManager
        
        # Create test data
        test_df = pd.DataFrame({
            'query': ['SELECT 1', 'SELECT 2', 'SELECT 3'],
            'description': ['Test 1', 'Test 2', 'Test 3']
        })
        
        print(f"🔍 Test DataFrame: {len(test_df)} rows")
        
        # Create embedding manager
        vector_store_path = Path(__file__).parent / "faiss_indices"
        status_path = Path(__file__).parent / "debug_status.json"
        
        manager = EmbeddingManager(vector_store_path, status_path)
        print(f"✅ Created EmbeddingManager")
        
        # Test with small batch
        print(f"🔄 Processing small test batch...")
        start_time = time.time()
        vector_store, docs = manager.process_initial_batch(test_df, chunk_size=3)
        elapsed = time.time() - start_time
        
        print(f"✅ Test batch completed in {elapsed:.1f} seconds")
        print(f"✅ Created vector store with {len(docs) if docs else 0} documents")
        
        return True
        
    except Exception as e:
        print(f"❌ EmbeddingManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🔧 Embedding Debug Test")
    print("=" * 50)
    
    # Test 1: CSV loading
    df = test_csv_loading()
    if df is None:
        return
    
    # Test 2: Ollama availability
    if not test_ollama_availability():
        print("\n⚠️  Continuing despite Ollama issues...")
    
    # Test 3: EmbeddingManager with small data
    if test_embedding_manager():
        print("\n🎉 Small test passed! Now testing with actual CSV...")
        
        # Test 4: Real CSV with limited rows
        try:
            from actions.embedding_manager import EmbeddingManager
            
            vector_store_path = Path(__file__).parent / "faiss_indices" 
            status_path = Path(__file__).parent / "debug_status.json"
            manager = EmbeddingManager(vector_store_path, status_path)
            
            # Test with first 10 rows from real CSV
            print(f"\n🔄 Testing with first 10 rows from real CSV...")
            test_df = df.head(10)
            
            start_time = time.time()
            vector_store, docs = manager.process_initial_batch(test_df, chunk_size=10)
            elapsed = time.time() - start_time
            
            print(f"✅ Real CSV test completed in {elapsed:.1f} seconds")
            print(f"✅ Processed {len(docs) if docs else 0} documents")
            
        except Exception as e:
            print(f"❌ Real CSV test failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🏁 Debug test complete!")

if __name__ == "__main__":
    main()