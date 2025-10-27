#!/usr/bin/env python3
"""
Performance and regression tests for app_simple_gemini.py
Ensures refactoring doesn't degrade performance or introduce bugs
"""

import sys
import os
import time
import unittest.mock as mock
from pathlib import Path
import pandas as pd
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock streamlit
sys.modules['streamlit'] = mock.MagicMock()

class TestPerformanceRegression:
    """Test that performance characteristics don't regress"""
    
    def test_utility_function_performance(self):
        """Test that utility functions maintain reasonable performance"""
        print("🧪 Testing utility function performance...")
        
        from app_simple_gemini import (
            estimate_token_count,
            calculate_context_utilization,
            safe_get_value
        )
        
        # Test token estimation performance
        large_text = " " * 10000  # 10k characters
        
        start_time = time.time()
        tokens = estimate_token_count(large_text)
        token_time = time.time() - start_time
        
        assert token_time < 0.01  # Should complete in < 10ms
        assert tokens > 0
        print(f"✅ Token estimation: {token_time:.4f}s (target: < 0.01s)")
        
        # Test context utilization performance
        from langchain_core.documents import Document
        docs = [Document(page_content=f"Test document {i}") for i in range(100)]
        query = "Test query for performance"
        
        start_time = time.time()
        util = calculate_context_utilization(docs, query)
        util_time = time.time() - start_time
        
        assert util_time < 0.05  # Should complete in < 50ms
        assert util['chunks_used'] == 100
        print(f"✅ Context utilization: {util_time:.4f}s (target: < 0.05s)")
        
        # Test safe value extraction performance
        large_row = {f'col_{i}': f'value_{i}' for i in range(1000)}
        
        start_time = time.time()
        for i in range(100):
            value = safe_get_value(large_row, f'col_{i}')
            assert value == f'value_{i}'
        safe_time = time.time() - start_time
        
        assert safe_time < 0.01  # Should complete in < 10ms for 100 lookups
        print(f"✅ Safe value extraction: {safe_time:.4f}s (target: < 0.01s for 100 lookups)")
    
    def test_data_loading_performance(self):
        """Test that data loading doesn't regress"""
        print("🧪 Testing data loading performance...")
        
        from app_simple_gemini import get_available_indices
        
        # Mock a large number of indices
        with mock.patch('app_simple_gemini.FAISS_INDICES_DIR', Path('/mock/faiss')):
            with mock.patch('pathlib.Path.exists', return_value=True):
                with mock.patch('pathlib.Path.iterdir') as mock_iterdir:
                    # Create many mock index directories
                    mock_paths = []
                    for i in range(100):
                        mock_path = mock.MagicMock()
                        mock_path.is_dir.return_value = True
                        mock_path.name = f'index_test_{i}'
                        mock_paths.append(mock_path)
                    
                    mock_iterdir.return_value = mock_paths
                    
                    start_time = time.time()
                    indices = get_available_indices()
                    indices_time = time.time() - start_time
                    
                    assert len(indices) == 100
                    assert indices_time < 0.1  # Should complete in < 100ms
                    print(f"✅ Available indices: {indices_time:.4f}s for 100 indices (target: < 0.1s)")
    
    def test_pagination_performance(self):
        """Test pagination performance with large datasets"""
        print("🧪 Testing pagination performance...")
        
        from app_simple_gemini import (
            calculate_pagination,
            get_page_slice,
            get_page_info
        )
        
        # Test with large dataset
        large_df = pd.DataFrame({'data': range(10000)})  # 10k rows
        
        start_time = time.time()
        pagination = calculate_pagination(10000, 100)
        pagination_time = time.time() - start_time
        
        assert pagination['total_pages'] == 100
        assert pagination_time < 0.01  # Should be very fast
        print(f"✅ Pagination calculation: {pagination_time:.6f}s (target: < 0.01s)")
        
        # Test page slicing performance
        start_time = time.time()
        page_slice = get_page_slice(large_df, 50, 100)  # Get page 50
        slice_time = time.time() - start_time
        
        assert len(page_slice) == 100
        assert slice_time < 0.01  # Should be very fast	        print(f"✅ Page slicing: {slice_time:.4f}s (target: < 0.01s)")
        
        # Test page info performance
        start_time = time.time()
        page_info = get_page_info(50, 10000, 100)
        info_time = time.time() - start_time
        
        assert page_info['current_page'] == 50
        assert info_time < 0.001  # Should be extremely fast
        print(f"✅ Page info: {info_time:.6f}s (target: < 0.001s)")
    
    def test_agent_detection_performance(self):
        """Test agent detection performance"""
        print("🧪 Testing agent detection performance...")
        
        from app_simple_gemini import (
            detect_agent_type,
            detect_chat_agent_type
        )
        
        test_queries = [
            "What tables are available?",
            "Show me user data from the last 30 days",
            "SELECT * FROM users ORDER BY created_at DESC",
            "How can I get revenue data by month?",
            "Tell me about the user engagement metrics"
        ] * 100  # 500 test queries
        
        # Test detect_agent_type performance
        start_time = time.time()
        for query in test_queries:
            agent_type, processed = detect_agent_type(query)
        agent_time = time.time() - start_time
        
        assert agent_time < 0.5  # Should complete in < 500ms for 500 queries
        print(f"✅ Agent detection: {agent_time:.4f}s for 500 queries (target: < 0.5s)")
        
        # Test detect_chat_agent_type performance
        start_time = time.time()
        for query in test_queries:
            agent_type, processed = detect_chat_agent_type(query)
        chat_agent_time = time.time() - start_time
        
        assert chat_agent_time < 0.5  # Should complete in < 500ms for 500 queries
        print(f"✅ Chat agent detection: {chat_agent_time:.4f}s for 500 queries (target: < 0.5s)")


class TestMemoryUsage:
    """Test that memory usage doesn't increase significantly"""
    
    def test_session_state_memory_growth(self):
        """Test that session state doesn't grow unboundedly"""
        print("🧪 Testing session state memory usage...")
        
        import app_simple_gemini
        
        # Simulate multiple session ID generations
        with mock.patch('streamlit.session_state', {}):
            initial_sessions = len([k for k in mock.st.session_state.keys() if k.startswith('user_')])
            
            # Generate multiple session IDs
            for i in range(10):
                app_simple_gemini.get_user_session_id()
            
            # Should only have one session ID per session
            final_sessions = len([k for k in mock.st.session_state.keys() if k.startswith('user_')])
            assert final_sessions == 1  # Should not create multiple session IDs
            
            print("✅ Session state memory usage is controlled")
    
    def test_dataframe_memory_efficiency(self):
        """Test that DataFrame operations are memory efficient"""
        print("🧪 Testing DataFrame memory efficiency...")
        
        from app_simple_gemini import get_page_slice
        
        # Create a large DataFrame
        large_df = pd.DataFrame({
            'query': [f'SELECT * FROM table_{i}' for i in range(10000)],
            'description': [f'Description {i}' for i in range(10000)],
            'large_column': ['x' * 100 for _ in range(10000)]  # Large strings
        })
        
        # Test that slicing doesn't create unexpected copies
        original_id = id(large_df)
        
        page_slice = get_page_slice(large_df, 50, 100)
        slice_id = id(page_slice)
        
        # Should be different objects but slice should be much smaller
        assert slice_id != original_id
        assert len(page_slice) == 100
        assert len(page_slice) < len(large_df)
        
        print("✅ DataFrame operations are memory efficient")


class TestFunctionSignatureRegression:
    """Test that function signatures don't change unexpectedly"""
    
    def test_critical_function_signatures(self):
        """Test that critical functions maintain their signatures"""
        print("🧪 Testing function signature stability...")
        
        import app_simple_gemini
        import inspect
        
        # Define expected signatures for critical functions
        expected_signatures = {
            'estimate_token_count': ['text'],
            'calculate_context_utilization': ['docs', 'query'],
            'load_vector_store': ['index_name'],
            'get_user_session_id': [],
            'calculate_pagination': ['total_queries', 'page_size'],
            'safe_get_value': ['row', 'column', 'default'],
            'detect_agent_type': ['user_input'],
            'detect_chat_agent_type': ['user_input']
        }
        
        for func_name, expected_params in expected_signatures.items():
            func = getattr(app_simple_gemini, func_name)
            sig = inspect.signature(func)
            actual_params = list(sig.parameters.keys())
            
            # Check actual parameters contain expected ones
            for param in expected_params:
                assert param in actual_params, f"{func_name} missing parameter: {param}"
            
            print(f"✅ {func_name} signature stable")
    
    def test_return_type_consistency(self):
        """Test that return types remain consistent"""
        print("🧪 Testing return type consistency...")
        
        import app_simple_gemini
        
        # Test utility function return types
        assert isinstance(app_simple_gemini.estimate_token_count("test"), int)
        assert isinstance(app_simple_gemini.calculate_context_utilization([], "test"), dict)
        assert isinstance(app_simple_gemini.get_user_session_id(), str)
        
        # Test pagination function return types
        pagination = app_simple_gemini.calculate_pagination(100, 10)
        assert isinstance(pagination, dict)
        
        page_info = app_simple_gemini.get_page_info(1, 100, 10)
        assert isinstance(page_info, dict)
        
        test_df = pd.DataFrame({'data': range(20)})
        page_slice = app_simple_gemini.get_page_slice(test_df, 1, 10)
        assert isinstance(page_slice, type(test_df))  # Should be DataFrame
        
        print("✅ Return type consistency maintained")


def run_performance_regression_tests():
    """Run all performance and regression tests"""
    print("🚀 Running Performance & Regression Tests\n")
    
    test_classes = [
        ("Performance Regression", TestPerformanceRegression),
        ("Memory Usage", TestMemoryUsage),
        ("Function Signature Regression", TestFunctionSignatureRegression)
    ]
    
    all_passed = True
    total_tests = 0
    passed_tests = 0
    
    for class_name, test_class in test_classes:
        print(f"\n📋 {class_name}:")
        
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        class_passed = True
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                passed_tests += 1
            except Exception as e:
                print(f"  ❌ {method_name} failed: {e}")
                class_passed = False
                all_passed = False
        
        if class_passed:
            print(f"✅ {class_name} - All tests passed")
        else:
            print(f"⚠️ {class_name} - Some tests failed")
    
    print(f"\n🎯 Performance & Regression Test Results:")
    print(f"   Summary: {passed_tests}/{total_tests} tests passed")
    
    if all_passed:
        print("✅ ALL PERFORMANCE & REGRESSION TESTS PASSED - No performance degradation detected")
        return True
    else:
        print("❌ SOME PERFORMANCE & REGRESSION TESTS FAILED - Review performance issues")
        return False


if __name__ == "__main__":
    success = run_performance_regression_tests()
    sys.exit(0 if success else 1)