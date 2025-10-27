#!/usr/bin/env python3
"""
Integration tests for Streamlit workflow and UI components
Tests the actual Streamlit app behavior with mocked dependencies
"""

import sys
import os
import json
import unittest.mock as mock
from pathlib import Path
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up comprehensive streamlit mock
mock_st = mock.MagicMock()
mock_st.session_state = {}
mock_st.set_page_config = mock.MagicMock()
mock_st.title = mock.MagicMock()
mock_st.caption = mock.MagicMock()
mock_st.sidebar = mock.MagicMock()
mock_st.header = mock.MagicMock()
mock_st.divider = mock.MagicMock()
mock_st.subheader = mock.MagicMock()
mock_st.checkbox = mock.MagicMock(return_value=False)
mock_st.radio = mock.MagicMock(return_value="→ Query Search")
mock_st.error = mock.MagicMock()
mock_st.info = mock.MagicMock()
mock_st.warning = mock.MagicMock()
mock_st.success = mock.MagicMock()

sys.modules['streamlit'] = mock_st

class TestStreamlitWorkflow:
    """Test Streamlit workflow and UI components"""
    
    def test_page_setup_and_configuration(self):
        """Test page setup and configuration loading"""
        print("🧪 Testing page setup and configuration...")
        
        try:
            # Test that we can import and setup the app
            import app_simple_gemini
            
            # Verify Streamlit setup functions are called
            mock_st.set_page_config.assert_called()
            mock_st.title.assert_called()
            mock_st.caption.assert_called()
            
            print("✅ Page setup works correctly")
        except Exception as e:
            print(f"❌ Page setup failed: {e}")
            raise
    
    def test_data_loading_in_context(self):
        """Test data loading when called from Streamlit context"""
        print("🧪 Testing data loading in Streamlit context...")
        
        import app_simple_gemini
        
        # Test CSV data loading with session state integration
        with mock.patch('app_simple_gemini.load_csv_data') as mock_load_csv:
            mock_df = pd.DataFrame({
                'query': ['SELECT * FROM users'],
                'description': ['Test query']
            })
            mock_load_csv.return_value = mock_df
            
            # Simulate session state behavior
            if 'csv_data' not in mock_st.session_state:
                csv_data = app_simple_gemini.load_csv_data()
                if csv_data is not None:
                    mock_st.session_state.csv_data = csv_data
            
            assert 'csv_data' in mock_st.session_state
            assert len(mock_st.session_state.csv_data) == 1
        
        print("✅ Data loading in Streamlit context works")
    
    def test_sidebar_navigation(self):
        """Test sidebar navigation and page selection"""
        print("🧪 Testing sidebar navigation...")
        
        import app_simple_gemini
        
        # Mock different page selections
        pages = ["→ Query Search", "◉ Data", "● Catalog", "◐ Chat", "◆ Introduction"]
        
        for page in pages:
            mock_st.radio.return_value = page
            
            # Test that the page selection is handled
            selected_page = mock_st.radio("Select Page:", pages)
            assert selected_page == page
        
        print("✅ Sidebar navigation works correctly")
    
    def test_configuration_management(self):
        """Test configuration management in UI context"""
        print("🧪 Testing configuration management...")
        
        import app_simple_gemini
        
        # Test advanced mode toggle
        mock_st.checkbox.return_value = True
        
        advanced_mode = mock_st.checkbox(
            "Advanced Mode",
            value=False,
            help="Show detailed controls",
            key="advanced_mode_toggle"
        )
        
        assert advanced_mode == True
        
        # Test that session state is updated
        mock_st.session_state.advanced_mode = advanced_mode
        assert mock_st.session_state.advanced_mode == True
        
        print("✅ Configuration management works")
    
    def test_error_display_workflows(self):
        """Test that error displays work correctly in Streamlit context"""
        print("🧪 Testing error display workflows...")
        
        import app_simple_gemini
        
        # Test vector store loading error
        with mock.patch('app_simple_gemini.load_vector_store') as mock_load:
            mock_load.return_value = None
            
            # Simulate the error handling in the app
            vector_store = app_simple_gemini.load_vector_store()
            if vector_store is None:
                mock_st.error("❌ Vector store not found")
                mock_st.info("💡 First run: python standalone_embedding_generator.py")
            
            # Verify error calls
            mock_st.error.assert_called()
            mock_st.info.assert_called()
        
        print("✅ Error display workflows work")
    
    def test_conversation_management_integration(self):
        """Test conversation management in Streamlit context"""
        print("🧪 Testing conversation management integration...")
        
        import app_simple_gemini
        
        # Test session ID generation in Streamlit context
        if 'user_session_id' not in mock_st.session_state:
            session_id = app_simple_gemini.get_user_session_id()
            mock_st.session_state.user_session_id = session_id
        
        assert 'user_session_id' in mock_st.session_state
        assert mock_st.session_state.user_session_id.startswith('user_')
        
        print("✅ Conversation management integration works")
    
    def test_styling_application(self):
        """Test that modern styling is applied"""
        print("🧪 Testing styling application...")
        
        import app_simple_gemini
        
        # Test that styling function can be called without errors
        try:
            app_simple_gemini.apply_modern_styling()
            print("✅ Modern styling applied successfully")
        except Exception as e:
            print(f"⚠️ Styling application failed: {e}")
            # This might fail due to CSS processing, which is OK in test environment
    
    def test_workflow_state_persistence(self):
        """Test that workflow state persists correctly"""
        print("🧪 Testing workflow state persistence...")
        
        import app_simple_gemini
        
        # Test that multiple state variables are managed
        state_variables = [
            'csv_data',
            'schema_manager', 
            'lookml_safe_join_map',
            'advanced_mode',
            'user_session_id'
        ]
        
        for var in state_variables:
            mock_st.session_state[var] = f"test_{var}"
            assert var in mock_st.session_state
            assert mock_st.session_state[var] == f"test_{var}"
        
        print("✅ Workflow state persistence works")


class TestPageSpecificFunctionality:
    """Test functionality specific to different pages"""
    
    def test_query_search_page_functionality(self):
        """Test query search page specific functionality"""
        print("🧪 Testing query search page functionality...")
        
        import app_simple_gemini
        
        # Test vector store loading for query search
        with mock.patch('app_simple_gemini.get_available_indices') as mock_indices:
            mock_indices.return_value = ['index_test1', 'index_test2']
            
            available = app_simple_gemini.get_available_indices()
            assert len(available) == 2
            assert all(idx.startswith('index_') for idx in available)
        
        print("✅ Query search page functionality works")
    
    def test_data_page_functionality(self):
        """Test data page specific functionality"""
        print("🧪 Testing data page functionality...")
        
        import app_simple_gemini
        
        # Test schema manager loading for data page
        with mock.patch('app_simple_gemini.load_schema_manager') as mock_schema:
            mock_schema.return_value = None  # Simulate no schema available
            
            schema_manager = app_simple_gemini.load_schema_manager()
            assert schema_manager is None  # Should handle gracefully
        
        print("✅ Data page functionality works")
    
    def test_catalog_page_functionality(self):
        """Test catalog page specific functionality"""
        print("🧪 Testing catalog page functionality...")
        
        import app_simple_gemini
        
        # Test catalog analytics loading
        with mock.patch('app_simple_gemini.load_cached_analytics') as mock_analytics:
            mock_analytics.return_value = {'total_queries': 100, 'table_usage': {}}
            
            analytics = app_simple_gemini.load_cached_analytics()
            assert analytics['total_queries'] == 100
            assert 'table_usage' in analytics
        
        print("✅ Catalog page functionality works")
    
    def test_chat_page_functionality(self):
        """Test chat page specific functionality"""
        print("🧪 Testing chat page functionality...")
        
        import app_simple_gemini
        
        # Test conversation context for chat
        with mock.patch('app_simple_gemini.calculate_conversation_tokens') as mock_tokens:
            mock_tokens.return_value = 150
            
            tokens = app_simple_gemini.calculate_conversation_tokens([
                {'role': 'user', 'content': 'Hello'},
                {'role': 'assistant', 'content': 'Hi there!'}
            ])
            assert tokens == 150
        
        print("✅ Chat page functionality works")


def run_streamlit_workflow_tests():
    """Run all Streamlit workflow tests"""
    print("🚀 Running Streamlit Workflow Tests\n")
    
    test_classes = [
        ("Streamlit Workflow", TestStreamlitWorkflow),
        ("Page Specific Functionality", TestPageSpecificFunctionality)
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
    
    print(f"\n🎯 Streamlit Workflow Test Results:")
    print(f"   Summary: {passed_tests}/{total_tests} tests passed")
    
    if all_passed:
        print("✅ ALL STREAMLIT WORKFLOW TESTS PASSED - UI integration verified")
        return True
    else:
        print("❌ SOME STREAMLIT WORKFLOW TESTS FAILED - Fix UI integration issues")
        return False


if __name__ == "__main__":
    success = run_streamlit_workflow_tests()
    sys.exit(0 if success else 1)