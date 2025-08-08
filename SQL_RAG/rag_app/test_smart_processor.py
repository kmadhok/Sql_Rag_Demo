#!/usr/bin/env python3
"""
Test script for the new SmartEmbeddingProcessor
"""

import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from smart_embedding_processor import SmartEmbeddingProcessor
from data_source_manager import DataSourceManager

def test_csv_processing():
    """Test processing with the actual CSV file"""
    print("🧪 Testing SmartEmbeddingProcessor with CSV data")
    print("=" * 60)
    
    # Paths
    csv_path = '/Users/kanumadhok/Sql_Rag_Demo/SQL_RAG/sample_test.csv'
    vector_store_path = Path(__file__).parent / "test_vector_store"
    status_path = Path(__file__).parent / "test_processor_status.json"
    
    try:
        # Create data source
        print("📂 Creating data source...")
        data_source = DataSourceManager.create_csv_source(csv_path)
        df = data_source.load_data()
        print(f"✅ Loaded {len(df)} rows from CSV")
        print(f"   Columns: {list(df.columns)}")
        
        # Initialize processor
        print("\n🔧 Initializing SmartEmbeddingProcessor...")
        processor = SmartEmbeddingProcessor(vector_store_path, status_path)
        print("✅ Processor initialized")
        
        # Test with small batch first (first 20 rows)
        print(f"\n🔄 Testing with first 20 rows...")
        test_df = df.head(20)
        
        start_time = time.time()
        vector_store, stats = processor.process_dataframe(
            test_df,
            source_name="csv_test_small",
            source_info=data_source.get_source_info(),
            initial_batch_size=10
        )
        elapsed = time.time() - start_time
        
        print(f"✅ Small batch completed in {elapsed:.1f}s")
        print(f"   Stats: {stats}")
        
        # Test search functionality
        print(f"\n🔍 Testing search functionality...")
        results = vector_store.similarity_search("SELECT customer", k=3)
        print(f"✅ Search returned {len(results)} results")
        
        if results:
            print("   Sample result:")
            print(f"   Content: {results[0].page_content[:100]}...")
            print(f"   Metadata: {results[0].metadata}")
        
        # Test incremental update (re-run with same data)
        print(f"\n🔄 Testing incremental update (same data)...")
        start_time = time.time()
        vector_store2, stats2 = processor.process_dataframe(
            test_df,
            source_name="csv_test_small",
            source_info=data_source.get_source_info(),
            initial_batch_size=10
        )
        elapsed2 = time.time() - start_time
        
        print(f"✅ Incremental update completed in {elapsed2:.1f}s")
        print(f"   Stats: {stats2}")
        print(f"   Cache hit: {stats2.get('cache_hit', False)}")
        
        # Test with larger batch (first 100 rows)
        print(f"\n🔄 Testing with first 100 rows...")
        test_df_large = df.head(100)
        
        start_time = time.time()
        vector_store3, stats3 = processor.process_dataframe(
            test_df_large,
            source_name="csv_test_large", 
            source_info=data_source.get_source_info(),
            initial_batch_size=50
        )
        elapsed3 = time.time() - start_time
        
        print(f"✅ Large batch completed in {elapsed3:.1f}s")
        print(f"   Stats: {stats3}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_composite_embedding():
    """Test composite embedding with multiple fields"""
    print("\n🧪 Testing Composite Embedding Strategy")
    print("=" * 60)
    
    import pandas as pd
    
    # Create test data with multiple fields
    test_data = pd.DataFrame({
        'query': [
            'SELECT * FROM customers WHERE status = "active"',
            'SELECT COUNT(*) FROM orders WHERE date >= "2024-01-01"',
            'SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id'
        ],
        'description': [
            'Get all active customers',
            'Count orders from this year',
            'Customer order summary with joins'
        ],
        'table': [
            'customers',
            'orders', 
            'customers, orders'
        ],
        'joins': [
            '',
            '',
            'customers.id = orders.customer_id'
        ]
    })
    
    print(f"📊 Test data: {len(test_data)} rows with composite fields")
    
    try:
        vector_store_path = Path(__file__).parent / "test_composite_store"
        status_path = Path(__file__).parent / "test_composite_status.json"
        
        processor = SmartEmbeddingProcessor(vector_store_path, status_path)
        
        start_time = time.time()
        vector_store, stats = processor.process_dataframe(
            test_data,
            source_name="composite_test",
            source_info="composite_fields_test",
            initial_batch_size=5
        )
        elapsed = time.time() - start_time
        
        print(f"✅ Composite embedding completed in {elapsed:.1f}s")
        print(f"   Stats: {stats}")
        
        # Test search with different field types
        print(f"\n🔍 Testing search across composite fields...")
        
        queries = [
            "customers table",
            "active status", 
            "join operations",
            "count orders"
        ]
        
        for query in queries:
            results = vector_store.similarity_search(query, k=2)
            print(f"   Query '{query}': {len(results)} results")
            if results:
                metadata = results[0].metadata
                print(f"     Best match: row {metadata.get('row_index', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Composite test failed: {e}")
        import traceback 
        traceback.print_exc()
        return False

def main():
    print("🚀 Smart Embedding Processor Test Suite")
    print("=" * 60)
    
    # Test 1: Basic CSV processing
    success1 = test_csv_processing()
    
    # Test 2: Composite embeddings
    success2 = test_composite_embedding()
    
    print("\n" + "=" * 60)
    print("📋 Test Results Summary:")
    print(f"   CSV Processing: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"   Composite Embeddings: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    if success1 and success2:
        print("\n🎉 All tests PASSED!")
        return True
    else:
        print("\n❌ Some tests FAILED!")
        return False

if __name__ == "__main__":
    main()