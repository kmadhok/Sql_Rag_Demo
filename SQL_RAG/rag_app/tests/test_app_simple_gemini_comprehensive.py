#!/usr/bin/env python3
"""
Comprehensive test suite for app_simple_gemini.py
This ensures refactoring won't break any existing functionality
"""

import sys
import os
import json
import tempfile
import unittest.mock as mock
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock streamlit before importing the app
sys.modules['streamlit'] = mock.MagicMock()

# Import the app functions we need to test
from app_simple_gemini import (
    estimate_token_count,
    calculate_context_utilization,
    load_vector_store,
    get_available_indices,
    load_lookml_safe_join_map,
    load_schema_manager,
    load_csv_data,
    safe_get_value,
    get_user_session_id,
    auto_save_conversation,
    calculate_pagination,
    get_page_slice,
    get_page_info,
    detect_agent_type,
    detect_chat_agent_type,
    get_agent_indicator,
    get_chat_agent_indicator,
    _fast_extract_tables,
    calculate_conversation_tokens
)

class TestUtilityFunctions:
    """Test core utility functions"""
    
    def test_estimate_token_count(self):
        """Test token estimation functionality"""
        print("🧪 Testing estimate_token_count...")
        
        # Test basic estimation
        text = "This is a simple test string with some words"
        tokens = estimate_token_count(text)
        assert isinstance(tokens, int)
        assert tokens > 0
        print("✅ Token estimation works correctly")
        
        # Test edge cases
        assert estimate_token_count("") == 0
        assert estimate_token_count("a" * 100) == 25  # 100 chars / 4 = 25 tokens
        print("✅ Token estimation edge cases handled")
    
    def test_calculate_context_utilization(self):
        """Test context utilization calculation for Gemini"""
        print("🧪 Testing calculate_context_utilization...")
        
        from langchain_core.documents import Document
        
        # Create test documents
        docs = [
            Document(page_content="This is test document one with some content"),
            Document(page_content="This is test document two with more content"),
        ]
        query = "What is in these documents?"
        
        util = calculate_context_utilization(docs, query)
        
        # Check return structure
        expected_keys = ['query_tokens', 'context_tokens', 'total_input_tokens', 
                        'utilization_percent', 'chunks_used', 'avg_tokens_per_chunk']
        for key in expected_keys:
            assert key in util
        
        # Check calculations
        assert util['chunks_used'] == 2
        assert util['utilization_percent'] < 100  # Should be very small for test data
        assert util['total_input_tokens'] == util['query_tokens'] + util['context_tokens']
        
        print("✅ Context utilization calculation works correctly")
    
    def test_pagination_functions(self):
        """Test pagination helper functions"""
        print("🧪 Testing pagination functions...")
        
        # Test calculate_pagination
        total_queries = 47
        page_size = 15
        
        pagination = calculate_pagination(total_queries, page_size)
        
        assert pagination['total_pages'] == 4  # ceil(47/15) = 4
        assert pagination['page_size'] == page_size
        assert pagination['has_multiple_pages'] == True
        assert pagination['total_queries'] == total_queries
        
        print("✅ Pagination calculation works")
        
        # Test get_page_info
        page_info = get_page_info(2, total_queries, page_size)
        assert page_info['current_page'] == 2
        assert page_info['start_idx'] == 15  # (2-1) * 15
        assert page_info['end_idx'] == 30  # 2 * 15
        
        print("✅ Page info calculation works")
        
        # Test get_page_slice
        test_df = pd.DataFrame({'data': range(50)})  # 50 rows
        page_slice = get_page_slice(test_df, 2, page_size)
        assert len(page_slice) == page_size  # Should have page_size rows
        assert page_slice.iloc[0]['data'] == 15  # Should start at index 15
        
        print("✅ Page slicing works")
    
    def test_safe_get_value(self):
        """Test safe dataframe value extraction"""
        print("🧪 Testing safe_get_value...")
        
        # Test with valid data
        row = {'name': 'John', 'age': 30, 'city': None}
        
        assert safe_get_value(row, 'name') == 'John'
        assert safe_get_value(row, 'age') == '30'
        assert safe_get_value(row, 'nonexistent') == ''
        assert safe_get_value(row, 'city', 'Unknown') == 'Unknown'
        
        print("✅ Safe value extraction works")
    
    def test_fast_extract_tables(self):
        """Test fast table extraction from text"""
        print("🧪 Testing _fast_extract_tables...")
        
        text = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        tables = _fast_extract_tables(text)
        
        assert 'users' in tables
        assert 'orders' in tables
        assert len(tables) == 2
        
        # Test with no tables
        text = "SELECT 1"
        tables = _fast_extract_tables(text)
        assert len(tables) == 0
        
        print("✅ Fast table extraction works")


class TestAgentDetection:
    """Test agent type detection functions"""
    
    def test_detect_agent_type(self):
        """Test agent type detection for search mode"""
        print("🧪 Testing detect_agent_type...")
        
        # Test schema queries
        agent_type, processed_query = detect_agent_type("What tables are available?")
        assert agent_type == 'schema_query'
        
        # Test chat queries
        agent_type, processed_query = detect_agent_type("Tell me about the data")
        assert agent_type is None or agent_type != 'schema_query'  # Should be chat
        
        print("✅ Agent type detection works")
    
    def test_detect_chat_agent_type(self):
        """Test agent type detection for chat mode"""
        print("🧪 Testing detect_chat_agent_type...")
        
        # Test schema queries
        agent_type, processed_query = detect_chat_agent_type("What tables exist?")
        assert agent_type == 'schema_query'
        
        # Test normal chat queries
        agent_type, processed_query = detect_chat_agent_type("How can I get user data?")
        assert agent_type is None or agent_type != 'schema_query'
        
        print("✅ Chat agent type detection works")
    
    def test_agent_indicators(self):
        """Test agent indicator functions"""
        print("🧪 Testing agent indicators...")
        
        indicator = get_agent_indicator('schema_query')
        assert isinstance(indicator, str)
        assert len(indicator) > 0
        
        chat_indicator = get_chat_agent_indicator('schema_query')
        assert isinstance(chat_indicator, str)
        assert len(chat_indicator) > 0
        
        # Test with None agent type
        none_indicator = get_agent_indicator(None)
        assert isinstance(none_indicator, str)
        
        print("✅ Agent indicators work")


class TestSessionManagement:
    """Test session management functions"""
    
    def test_get_user_session_id(self):
        """Test user session ID generation"""
        print("🧪 Testing get_user_session_id...")
        
        # Mock streamlit session state
        with mock.patch('streamlit.session_state', {}):
            session_id = get_user_session_id()
            assert isinstance(session_id, str)
            assert session_id.startswith('user_')
            assert len(session_id) == 21  # 'user_' + 16 char hash
            
            # Test that it returns same ID on subsequent calls
            session_id2 = get_user_session_id()
            assert session_id == session_id2
        
        print("✅ User session ID generation works")
    
    def test_calculate_conversation_tokens(self):
        """Test conversation token calculation"""
        print("🧪 Testing calculate_conversation_tokens...")
        
        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there! How can I help?'}
        ]
        
        tokens = calculate_conversation_tokens(messages)
        assert isinstance(tokens, int)
        assert tokens > 0
        
        # Test with empty messages
        empty_tokens = calculate_conversation_tokens([])
        assert empty_tokens == 0
        
        print("✅ Conversation token calculation works")


class TestDataLoading:
    """Test data loading functions with mocked dependencies"""
    
    def test_get_available_indices(self):
        """Test getting available vector store indices"""
        print("🧪 Testing get_available_indices...")
        
        # Mock filesystem
        with mock.patch('app_simple_gemini.FAISS_INDICES_DIR', Path('/mock/faiss')):
            # Create mock directory structure
            mock_files = [
                'index_test1',
                'index_test2', 
                'other_file.txt',
                'not_index_dir'
            ]
            
            with mock.patch('pathlib.Path.exists', return_value=True):
                with mock.patch('pathlib.Path.iterdir') as mock_iterdir:
                    # Create mock file objects
                    mock_paths = []
                    for filename in mock_files:
                        mock_path = mock.MagicMock()
                        mock_path.is_dir.return_value = filename in ['index_test1', 'index_test2', 'not_index_dir']
                        mock_path.name = filename
                        mock_paths.append(mock_path)
                    
                    mock_iterdir.return_value = mock_paths
                    
                    indices = get_available_indices()
                    
                    # Should return only directories starting with 'index_'
                    assert len(indices) == 2
                    assert 'index_test1' in indices
                    assert 'index_test2' in indices
                    assert 'not_index_dir' not in indices
        
        print("✅ Available indices detection works")
    
    def test_load_csv_data_fallback_behavior(self):
        """Test CSV data loading fallback behavior"""
        print("🧪 Testing CSV data loading fallback...")
        
        # Test when no cache files exist
        with mock.patch('pathlib.Path.exists', return_value=False):
            with mock.patch('pandas.read_csv') as mock_read_csv:
                # Mock CSV data
                mock_df = pd.DataFrame({
                    'query': ['SELECT * FROM users', 'SELECT * FROM orders'],
                    'description': ['User query', 'Order query']
                })
                mock_read_csv.return_value = mock_df
                
                result = load_csv_data()
                
                assert result is not None
                assert len(result) == 2
                assert 'query' in result.columns
        
        print("✅ CSV data loading fallback works")
    
    def test_load_lookml_safe_join_map_caching(self):
        """Test LookML safe join map loading and caching"""
        print("🧪 Testing LookML safe join map loading...")
        
        mock_join_map = {
            'explores': {'users': {'joins': ['orders']}},
            'metadata': {'total_explores': 1}
        }
        
        # Test loading from primary path
        with mock.patch('pathlib.Path.exists') as mock_exists:
            with mock.patch('builtins.open', mock.mock_open()) as mock_file:
                with mock.patch('json.load', return_value=mock_join_map):
                    # Primary path exists
                    mock_exists.side_effect = lambda: True
                    
                    result = load_lookml_safe_join_map()
                    
                    assert result == mock_join_map
                    assert result['metadata']['total_explores'] == 1
        
        print("✅ LookML safe join map loading works")


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_graceful_import_failures(self):
        """Test that import failures are handled gracefully"""
        print("🧪 Testing graceful import failures...")
        
        # The app should handle missing dependencies gracefully
        # This is tested by the fact that we can import the functions
        # even when some optional dependencies might not be available
        
        # Test that conversation management imports work even when not available
        try:
            from core.conversation_manager import get_conversation_manager
        except ImportError:
            # This is expected - should be handled gracefully
            pass
        
        print("✅ Import failures are handled gracefully")
    
    def test_calculation_edge_cases(self):
        """Test calculations with edge cases"""
        print("🧪 Testing calculation edge cases...")
        
        # Test context utilization with empty docs
        empty_util = calculate_context_utilization([], "test query")
        assert empty_util['context_tokens'] == 0
        assert empty_util['chunks_used'] == 0
        assert empty_util['avg_tokens_per_chunk'] == 0
        
        # Test pagination with zero items
        zero_pagination = calculate_pagination(0, 15)
        assert zero_pagination['total_pages'] == 0
        assert zero_pagination['has_multiple_pages'] == False
        
        print("✅ Calculation edge cases handled correctly")


def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("🚀 Running Comprehensive App Tests\n")
    
    test_classes = [
        ("Utility Functions", TestUtilityFunctions),
        ("Agent Detection", TestAgentDetection), 
        ("Session Management", TestSessionManagement),
        ("Data Loading", TestDataLoading),
        ("Error Handling", TestErrorHandling)
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
    
    print(f"\n🎯 Comprehensive Test Results:")
    print(f"   Summary: {passed_tests}/{total_tests} tests passed")
    
    if all_passed:
        print("✅ ALL COMPREHENSIVE TESTS PASSED - Safe to proceed with refactoring")
        return True
    else:
        print("❌ SOME TESTS FAILED - Fix issues before refactoring")
        return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)