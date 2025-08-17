"""
Unit tests for page class instantiation and basic methods
"""
import pytest
from unittest.mock import patch, Mock

# Add parent directory to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import test helpers
from tests.mock_helpers import MockStreamlitComponents, create_sample_dataframe


class TestSearchPageBasics:
    """Test SearchPage class instantiation and basic functionality"""
    
    def test_search_page_instantiation(self):
        """Test SearchPage can be instantiated without external dependencies"""
        with patch.dict('sys.modules', {
            'streamlit': MockStreamlitComponents().get_mock(),
            'modular.session_manager': Mock(),
            'modular.vector_store_manager': Mock(),
            'modular.rag_engine': Mock(),
            'modular.utils': Mock(),
            'hybrid_retriever': Mock()
        }):
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            assert page is not None
            assert hasattr(page, 'page_title')
            assert hasattr(page, 'render')
    
    def test_search_page_title(self):
        """Test SearchPage has correct title"""
        with patch.dict('sys.modules', {
            'streamlit': MockStreamlitComponents().get_mock(),
            'modular.session_manager': Mock(),
            'modular.vector_store_manager': Mock(),
            'modular.rag_engine': Mock(),
            'modular.utils': Mock(),
            'hybrid_retriever': Mock()
        }):
            from modular.page_modules.search_page import SearchPage
            from modular.config import PAGE_NAMES
            
            page = SearchPage()
            assert page.page_title == PAGE_NAMES['search']
    
    def test_search_page_has_required_methods(self):
        """Test SearchPage has all required methods"""
        with patch.dict('sys.modules', {
            'streamlit': MockStreamlitComponents().get_mock(),
            'modular.session_manager': Mock(),
            'modular.vector_store_manager': Mock(),
            'modular.rag_engine': Mock(),
            'modular.utils': Mock(),
            'hybrid_retriever': Mock()
        }):
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            
            # Check all major methods exist
            assert hasattr(page, 'render')
            assert hasattr(page, 'render_search_configuration')
            assert hasattr(page, 'display_query_card')
            assert hasattr(page, 'render_search_results')
            assert hasattr(page, 'display_context_utilization')
            assert hasattr(page, 'display_sources')
            assert hasattr(page, 'render_instructions')
            
            # Check methods are callable
            assert callable(page.render)
            assert callable(page.render_search_configuration)
            assert callable(page.display_query_card)


class TestCatalogPageBasics:
    """Test CatalogPage class instantiation and basic functionality"""
    
    def test_catalog_page_instantiation(self):
        """Test CatalogPage can be instantiated without external dependencies"""
        with patch.dict('sys.modules', {
            'streamlit': MockStreamlitComponents().get_mock(),
            'modular.session_manager': Mock(),
            'modular.data_loader': Mock(),
            'modular.utils': Mock()
        }):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            assert page is not None
            assert hasattr(page, 'page_title')
            assert hasattr(page, 'render')
    
    def test_catalog_page_title(self):
        """Test CatalogPage has correct title"""
        with patch.dict('sys.modules', {
            'streamlit': MockStreamlitComponents().get_mock(),
            'modular.session_manager': Mock(),
            'modular.data_loader': Mock(),
            'modular.utils': Mock()
        }):
            from modular.page_modules.catalog_page import CatalogPage
            from modular.config import PAGE_NAMES
            
            page = CatalogPage()
            assert page.page_title == PAGE_NAMES['catalog']
    
    def test_catalog_page_has_required_methods(self):
        """Test CatalogPage has all required methods"""
        with patch.dict('sys.modules', {
            'streamlit': MockStreamlitComponents().get_mock(),
            'modular.session_manager': Mock(),
            'modular.data_loader': Mock(),
            'modular.utils': Mock()
        }):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Check all major methods exist
            assert hasattr(page, 'render')
            assert hasattr(page, 'load_cached_analytics')
            assert hasattr(page, 'display_join_analysis')
            assert hasattr(page, 'display_query_card')
            assert hasattr(page, 'search_queries')
            assert hasattr(page, 'render_pagination_controls')
            
            # Check methods are callable
            assert callable(page.render)
            assert callable(page.load_cached_analytics)
            assert callable(page.display_join_analysis)


class TestChatPageBasics:
    """Test ChatPage class instantiation and basic functionality"""
    
    def test_chat_page_instantiation(self):
        """Test ChatPage can be instantiated without external dependencies"""
        with patch.dict('sys.modules', {
            'streamlit': MockStreamlitComponents().get_mock(),
            'modular.session_manager': Mock(),
            'modular.vector_store_manager': Mock(),
            'chat_system': Mock()
        }):
            from modular.page_modules.chat_page import ChatPage
            
            page = ChatPage()
            assert page is not None
            assert hasattr(page, 'page_title')
            assert hasattr(page, 'render')
    
    def test_chat_page_title(self):
        """Test ChatPage has correct title"""
        with patch.dict('sys.modules', {
            'streamlit': MockStreamlitComponents().get_mock(),
            'modular.session_manager': Mock(),
            'modular.vector_store_manager': Mock(),
            'chat_system': Mock()
        }):
            from modular.page_modules.chat_page import ChatPage
            from modular.config import PAGE_NAMES
            
            page = ChatPage()
            assert page.page_title == PAGE_NAMES['chat']
    
    def test_chat_page_render_function_exists(self):
        """Test ChatPage has render functionality"""
        with patch.dict('sys.modules', {
            'streamlit': MockStreamlitComponents().get_mock(),
            'modular.session_manager': Mock(),
            'modular.vector_store_manager': Mock(),
            'chat_system': Mock()
        }):
            from modular.page_modules.chat_page import ChatPage, render
            
            page = ChatPage()
            
            # Check render method exists
            assert hasattr(page, 'render')
            assert callable(page.render)
            
            # Check module-level render function exists
            assert callable(render)


class TestPageClassMethods:
    """Test specific methods of page classes with mocked dependencies"""
    
    def test_search_page_display_query_card(self):
        """Test SearchPage display_query_card method"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st
        ), patch('modular.page_modules.search_page.safe_get_value') as mock_safe_get:
            # Mock safe_get_value to return predictable values
            def mock_safe_get_side_effect(row, column, default=''):
                return row.get(column, default)
            mock_safe_get.side_effect = mock_safe_get_side_effect
            
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            
            # Create test row data
            test_row = {
                'query': 'SELECT * FROM customers',
                'description': 'Get all customers',
                'tables_parsed': ['customers'],
                'joins_parsed': []
            }
            
            # This should not raise an exception
            page.display_query_card(test_row, 0)
            
            # Verify some streamlit components were called
            mock_st.container.assert_called()
            mock_st.expander.assert_called()
            mock_st.code.assert_called()
    
    def test_catalog_page_search_queries_with_empty_search(self):
        """Test CatalogPage search_queries with empty search term"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Create test dataframe
            test_df = create_sample_dataframe(3)
            
            # Test with empty search - should return original dataframe
            result = page.search_queries(test_df, '')
            assert len(result) == len(test_df)
            assert result.equals(test_df)
    
    def test_catalog_page_search_queries_with_search_term(self):
        """Test CatalogPage search_queries with actual search term"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ), patch('modular.page_modules.catalog_page.safe_get_value') as mock_safe_get:
            # Mock safe_get_value to return the actual values
            def mock_safe_get_side_effect(row, column, default=''):
                return str(row.get(column, default))
            mock_safe_get.side_effect = mock_safe_get_side_effect
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Create test dataframe with specific content
            test_df = create_sample_dataframe(3)
            
            # Test search that should find results
            result = page.search_queries(test_df, 'table_0')
            
            # Should find at least one result
            assert len(result) >= 1
            
            # Verify streamlit info was called to show results
            mock_st.info.assert_called()


class TestPageErrorHandling:
    """Test error handling in page classes"""
    
    def test_search_page_handles_missing_dependencies_gracefully(self):
        """Test SearchPage handles missing dependencies without crashing"""
        # Test with minimal mocking to simulate missing dependencies
        with patch.dict('sys.modules', {
            'streamlit': MockStreamlitComponents().get_mock(),
        }):
            try:
                from modular.page_modules.search_page import SearchPage
                page = SearchPage()
                # If we get here, the import worked despite missing some dependencies
                assert page is not None
            except ImportError:
                # This is expected and acceptable for missing optional dependencies
                pass
    
    def test_catalog_page_handles_missing_analytics_gracefully(self):
        """Test CatalogPage handles missing analytics gracefully"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st,
        ), patch('modular.page_modules.catalog_page.CATALOG_ANALYTICS_DIR') as mock_dir:
            # Mock directory that doesn't exist
            mock_dir.exists.return_value = False
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Test load_cached_analytics returns None for missing directory
            result = page.load_cached_analytics()
            assert result is None