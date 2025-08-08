#!/usr/bin/env python3
"""
Windows Compatibility Test Suite

Comprehensive tests to validate Windows-specific embedding processing
and ensure the application works correctly on Windows systems.

Usage:
    python test_windows_compatibility.py
    python test_windows_compatibility.py --verbose
    python test_windows_compatibility.py --quick
"""

import os
import sys
import time
import tempfile
import argparse
import platform
import multiprocessing
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# Test imports and availability
def test_imports():
    """Test that all required packages are available"""
    print("🔍 Testing package imports...")
    
    import_results = {}
    required_packages = [
        ('pandas', 'pd'),
        ('langchain_ollama', 'OllamaEmbeddings'),
        ('langchain_community.vectorstores', 'FAISS'),
        ('langchain_core.documents', 'Document'),
        ('windows_embedding_processor', 'get_embedding_processor'),
        ('data_source_manager', 'DataSourceManager'),
        ('standalone_embedding_generator', 'StandaloneEmbeddingGenerator')
    ]
    
    for package, component in required_packages:
        try:
            if component:
                exec(f"from {package} import {component}")
            else:
                exec(f"import {package}")
            import_results[package] = "✅ Available"
        except ImportError as e:
            import_results[package] = f"❌ Missing: {e}"
    
    # Print results
    all_available = True
    for package, status in import_results.items():
        print(f"  {package}: {status}")
        if "❌" in status:
            all_available = False
    
    return all_available


def test_ollama_connection():
    """Test Ollama availability and required models"""
    print("\n🔍 Testing Ollama connection...")
    
    try:
        from langchain_ollama import OllamaEmbeddings
        
        # Test embedding model
        print("  Testing nomic-embed-text model...")
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        # Test with a simple query
        test_embedding = embeddings.embed_query("test connection")
        
        if len(test_embedding) > 0:
            print("  ✅ Ollama nomic-embed-text model working")
            return True
        else:
            print("  ❌ Ollama returned empty embedding")
            return False
            
    except Exception as e:
        print(f"  ❌ Ollama connection failed: {e}")
        print("  💡 Make sure Ollama is running: ollama serve")
        print("  💡 Make sure model is available: ollama pull nomic-embed-text")
        return False


def create_test_data() -> pd.DataFrame:
    """Create test DataFrame with sample queries"""
    return pd.DataFrame({
        'query': [
            'SELECT * FROM customers WHERE status = "active"',
            'SELECT COUNT(*) FROM orders WHERE order_date >= "2024-01-01"',
            'SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id',
            'SELECT AVG(total) as avg_order FROM orders',
            'SELECT category, SUM(quantity) FROM products GROUP BY category'
        ],
        'description': [
            'Get all active customers',
            'Count orders from this year',
            'Customer orders with join',
            'Calculate average order value',
            'Product quantities by category'
        ],
        'table': [
            'customers',
            'orders',
            'customers,orders',
            'orders',
            'products'
        ],
        'joins': [
            '',
            '',
            'c.id = o.customer_id',
            '',
            ''
        ]
    })


def test_windows_processor():
    """Test Windows-compatible embedding processor"""
    print("\n🔍 Testing Windows embedding processor...")
    
    try:
        from windows_embedding_processor import get_embedding_processor
        
        # Create test data
        test_df = create_test_data()
        
        # Initialize processor
        processor = get_embedding_processor(
            initial_batch_size=3,  # Small batch for testing
            max_workers=2         # Limited workers for test
        )
        
        def test_callback(message):
            print(f"    Progress: {message}")
        
        # Process embeddings
        print("  Processing test embeddings...")
        start_time = time.time()
        
        vector_store = processor.process_embeddings(
            test_df,
            "test_data",
            "test_source_info",
            progress_callback=test_callback
        )
        
        processing_time = time.time() - start_time
        doc_count = len(vector_store.docstore._dict)
        
        print(f"  ✅ Windows processor completed in {processing_time:.1f}s")
        print(f"  ✅ Created {doc_count} document embeddings")
        
        # Test similarity search
        results = vector_store.similarity_search("customer orders", k=2)
        print(f"  ✅ Similarity search returned {len(results)} results")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Windows processor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_standalone_generator(quick_test: bool = False):
    """Test standalone embedding generator"""
    print("\n🔍 Testing standalone embedding generator...")
    
    try:
        from standalone_embedding_generator import StandaloneEmbeddingGenerator
        
        # Create temporary test CSV
        test_df = create_test_data()
        if quick_test:
            test_df = test_df.head(2)  # Limit to 2 rows for quick test
        
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "test_queries.csv"
            output_dir = Path(temp_dir) / "test_faiss"
            
            # Save test data
            test_df.to_csv(csv_path, index=False)
            print(f"  Created test CSV with {len(test_df)} queries")
            
            # Create generator
            generator = StandaloneEmbeddingGenerator(
                csv_path=str(csv_path),
                output_dir=str(output_dir),
                batch_size=2,
                max_workers=2,
                verbose=False
            )
            
            # Generate embeddings
            print("  Generating embeddings...")
            start_time = time.time()
            success = generator.generate(force_rebuild=True)
            processing_time = time.time() - start_time
            
            if success:
                print(f"  ✅ Standalone generator completed in {processing_time:.1f}s")
                
                # Verify output files
                index_files = list(output_dir.glob("index_*"))
                status_files = list(output_dir.glob("status_*.json"))
                
                print(f"  ✅ Created {len(index_files)} index directories")
                print(f"  ✅ Created {len(status_files)} status files")
                
                return True
            else:
                print("  ❌ Standalone generator failed")
                return False
                
    except Exception as e:
        print(f"  ❌ Standalone generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_csv_data_source():
    """Test CSV data source functionality"""
    print("\n🔍 Testing CSV data source...")
    
    try:
        from data_source_manager import DataSourceManager
        
        # Create temporary test CSV
        test_df = create_test_data()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "test_queries.csv"
            test_df.to_csv(csv_path, index=False)
            
            # Test CSV data source
            data_source = DataSourceManager.create_csv_source(csv_path)
            loaded_df = data_source.load_data()
            
            print(f"  ✅ Loaded {len(loaded_df)} rows from CSV")
            print(f"  ✅ Columns: {list(loaded_df.columns)}")
            print(f"  ✅ Source info: {data_source.get_source_info()}")
            
            # Verify data integrity
            assert len(loaded_df) == len(test_df), "Row count mismatch"
            assert set(loaded_df.columns) == set(test_df.columns), "Column mismatch"
            
            print("  ✅ CSV data source test passed")
            return True
            
    except Exception as e:
        print(f"  ❌ CSV data source test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiprocessing():
    """Test multiprocessing functionality on Windows"""
    print("\n🔍 Testing multiprocessing compatibility...")
    
    try:
        import multiprocessing
        
        def test_worker(x):
            return x * 2
        
        # Test process pool
        with multiprocessing.Pool(processes=2) as pool:
            test_data = [1, 2, 3, 4, 5]
            results = pool.map(test_worker, test_data)
            
            expected = [x * 2 for x in test_data]
            assert results == expected, "Multiprocessing results don't match"
            
            print("  ✅ Basic multiprocessing works")
        
        # Test ProcessPoolExecutor (used by our processors)
        from concurrent.futures import ProcessPoolExecutor
        
        with ProcessPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(test_worker, x) for x in test_data]
            results = [f.result() for f in futures]
            
            assert results == expected, "ProcessPoolExecutor results don't match"
            
            print("  ✅ ProcessPoolExecutor works")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Multiprocessing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_usage():
    """Test memory usage patterns"""
    print("\n🔍 Testing memory usage...")
    
    try:
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"  Initial memory usage: {initial_memory:.1f} MB")
        
        # Create test data that would use memory
        test_data = create_test_data()
        large_df = pd.concat([test_data] * 20, ignore_index=True)  # 100 rows
        
        # Force garbage collection
        gc.collect()
        
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory
        
        print(f"  Memory after test data: {current_memory:.1f} MB (+{memory_increase:.1f} MB)")
        
        if memory_increase < 100:  # Less than 100MB increase is reasonable
            print("  ✅ Memory usage is reasonable")
            return True
        else:
            print("  ⚠️  High memory usage detected")
            return False
            
    except ImportError:
        print("  ⚠️  psutil not available, skipping memory test")
        return True
    except Exception as e:
        print(f"  ❌ Memory test failed: {e}")
        return False


def test_file_operations():
    """Test file operations on Windows"""
    print("\n🔍 Testing file operations...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test directory creation
            test_dir = temp_path / "test_embeddings"
            test_dir.mkdir(exist_ok=True)
            assert test_dir.exists(), "Directory creation failed"
            
            # Test file writing/reading
            test_file = test_dir / "test.json"
            test_data = {"test": "data", "timestamp": time.time()}
            
            import json
            with open(test_file, 'w') as f:
                json.dump(test_data, f)
            
            assert test_file.exists(), "File creation failed"
            
            with open(test_file, 'r') as f:
                loaded_data = json.load(f)
            
            assert loaded_data["test"] == "data", "File read/write failed"
            
            # Test file deletion
            test_file.unlink()
            assert not test_file.exists(), "File deletion failed"
            
            print("  ✅ File operations work correctly")
            return True
            
    except Exception as e:
        print(f"  ❌ File operations test failed: {e}")
        return False


def run_performance_benchmark(quick: bool = False):
    """Run performance benchmark"""
    print("\n🔍 Running performance benchmark...")
    
    try:
        # Create larger test dataset
        base_df = create_test_data()
        if quick:
            test_df = pd.concat([base_df] * 4, ignore_index=True)  # 20 rows
        else:
            test_df = pd.concat([base_df] * 20, ignore_index=True)  # 100 rows
        
        print(f"  Benchmarking with {len(test_df)} queries...")
        
        from windows_embedding_processor import get_embedding_processor
        
        processor = get_embedding_processor(
            initial_batch_size=min(25, len(test_df) // 2),
            max_workers=min(4, multiprocessing.cpu_count())
        )
        
        # Benchmark processing time
        start_time = time.time()
        
        vector_store = processor.process_embeddings(
            test_df,
            "benchmark_data",
            "benchmark_source_info"
        )
        
        processing_time = time.time() - start_time
        queries_per_second = len(test_df) / processing_time
        
        print(f"  ✅ Processed {len(test_df)} queries in {processing_time:.1f}s")
        print(f"  ✅ Performance: {queries_per_second:.1f} queries/second")
        print(f"  ✅ Created {len(vector_store.docstore._dict)} document embeddings")
        
        # Performance thresholds
        if quick:
            expected_min_qps = 0.5  # At least 0.5 queries/second for quick test
        else:
            expected_min_qps = 1.0   # At least 1 query/second for full test
        
        if queries_per_second >= expected_min_qps:
            print(f"  ✅ Performance meets expectations (≥{expected_min_qps} q/s)")
            return True
        else:
            print(f"  ⚠️  Performance below expectations (<{expected_min_qps} q/s)")
            return False
            
    except Exception as e:
        print(f"  ❌ Performance benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_system_info():
    """Print system information for diagnostics"""
    print("🖥️  System Information:")
    print(f"  Platform: {platform.platform()}")
    print(f"  System: {platform.system()}")
    print(f"  Architecture: {platform.architecture()}")
    print(f"  Python: {platform.python_version()}")
    print(f"  CPU Count: {multiprocessing.cpu_count()}")
    
    try:
        import psutil
        memory = psutil.virtual_memory()
        print(f"  Total Memory: {memory.total / 1024 / 1024 / 1024:.1f} GB")
        print(f"  Available Memory: {memory.available / 1024 / 1024 / 1024:.1f} GB")
    except ImportError:
        print("  Memory info: Not available (psutil not installed)")
    
    print()


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Windows compatibility test suite")
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()
    
    print("🧪 Windows Compatibility Test Suite")
    print("=" * 50)
    
    # Print system information
    print_system_info()
    
    # Define test suite
    tests = [
        ("Package Imports", test_imports),
        ("Ollama Connection", test_ollama_connection),
        ("Multiprocessing", test_multiprocessing),
        ("File Operations", test_file_operations),
        ("Memory Usage", test_memory_usage),
        ("CSV Data Source", test_csv_data_source),
        ("Windows Processor", test_windows_processor),
        ("Standalone Generator", lambda: test_standalone_generator(quick_test=args.quick)),
        ("Performance Benchmark", lambda: run_performance_benchmark(quick=args.quick))
    ]
    
    # Run tests
    results = {}
    start_time = time.time()
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results[test_name] = "✅ PASS" if success else "❌ FAIL"
        except KeyboardInterrupt:
            print(f"\n⏹️  Test interrupted by user")
            results[test_name] = "⏹️ INTERRUPTED"
            break
        except Exception as e:
            print(f"❌ Unexpected error in {test_name}: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            results[test_name] = "❌ ERROR"
    
    # Print summary
    total_time = time.time() - start_time
    print(f"\n{'='*50}")
    print("🎯 Test Results Summary")
    print(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if "✅" in result)
    failed = sum(1 for result in results.values() if "❌" in result)
    total = len(results)
    
    for test_name, result in results.items():
        print(f"  {test_name:<25}: {result}")
    
    print(f"\n📊 Overall Results:")
    print(f"  Total Tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Success Rate: {passed/total*100:.1f}%" if total > 0 else "  Success Rate: 0%")
    print(f"  Total Time: {total_time:.1f}s")
    
    if failed == 0:
        print("\n🎉 All tests passed! Windows compatibility verified.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    # Set multiprocessing start method for Windows compatibility
    if platform.system() == 'Windows':
        multiprocessing.set_start_method('spawn', force=True)
    
    sys.exit(main())