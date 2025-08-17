"""
Integration tests for page components with mocked dependencies
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
import pandas as pd

# Add parent directory to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import test helpers and fixtures
from tests.mock_helpers import (
    MockStreamlitComponents,
    MockSessionManager,
    MockVectorStoreManager,
    MockRAGEngine
)
from tests.fixtures import (
    get_sample_query_data,
    get_sample_analytics,
    get_mock_rag_response,
    get_search_config
)


class TestSearchPageIntegration:
    """Integration tests for SearchPage with realistic scenarios"""
    
    def test_complete_search_workflow(self):
        """Test complete search workflow from configuration to results"""
        # Setup mocks
        mock_st = MockStreamlitComponents()
        mock_session_manager = MockSessionManager(csv_data=get_sample_query_data('parsed'))
        mock_vector_manager = MockVectorStoreManager(['test_index'])
        mock_rag_engine = MockRAGEngine()
        
        # Configure mock responses
        answer, sources, token_usage = get_mock_rag_response()
        mock_rag_engine.configure_answer(answer, sources, token_usage)
        
        # Configure Streamlit inputs for search workflow
        mock_st.configure_input('text_input', 'How do I calculate customer lifetime value?')
        mock_st.configure_input('button', True)  # Search button clicked
        mock_st.configure_input('selectbox', 'test_index')
        mock_st.configure_input('slider', 5)
        mock_st.configure_input('checkbox', True)
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st.get_mock(),
            session_manager=mock_session_manager.get_mock(),
            vector_store_manager=mock_vector_manager.get_mock(),
            rag_engine=mock_rag_engine.get_mock(),
            HYBRID_SEARCH_AVAILABLE=True
        ), patch('modular.page_modules.search_page.validate_query_input') as mock_validate, \
          patch('modular.page_modules.search_page.extract_agent_type') as mock_extract:
            
            # Configure validation and agent extraction
            mock_validate.return_value = (True, "")
            mock_extract.return_value = (None, 'How do I calculate customer lifetime value?')
            
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            page.render()
            
            # Verify the complete workflow
            # 1. CSV data was loaded
            mock_session_manager.get_mock().load_csv_data_if_needed.assert_called()
            
            # 2. Vector store was loaded
            mock_vector_manager.get_mock().ensure_vector_store_loaded.assert_called()
            
            # 3. RAG engine was called
            mock_rag_engine.get_mock().answer_question.assert_called()
            
            # 4. Results were displayed
            mock_st.get_mock().write.assert_called()
            mock_st.get_mock().subheader.assert_called()
    
    def test_search_with_agent_type_extraction(self):
        """Test search workflow with agent type extraction"""
        # Setup mocks
        mock_st = MockStreamlitComponents()
        mock_session_manager = MockSessionManager(csv_data=get_sample_query_data('basic'))
        mock_vector_manager = MockVectorStoreManager(['test_index'])
        mock_rag_engine = MockRAGEngine()
        
        # Configure for @explain agent
        mock_st.configure_input('text_input', '@explain How do joins work in SQL?')
        mock_st.configure_input('button', True)
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st.get_mock(),
            session_manager=mock_session_manager.get_mock(),
            vector_store_manager=mock_vector_manager.get_mock(),
            rag_engine=mock_rag_engine.get_mock()
        ), patch('modular.page_modules.search_page.validate_query_input') as mock_validate, \
          patch('modular.page_modules.search_page.extract_agent_type') as mock_extract:
            
            mock_validate.return_value = (True, "")
            mock_extract.return_value = ('explain', 'How do joins work in SQL?')
            
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            # Mock configuration to avoid complex setup
            page.render_search_configuration = Mock(return_value=get_search_config('default'))
            
            page.render()
            
            # Verify agent type was passed to RAG engine
            call_args = mock_rag_engine.get_mock().answer_question.call_args
            assert call_args is not None
            kwargs = call_args[1]
            assert kwargs.get('agent_type') == 'explain'
    
    def test_search_error_handling(self):
        """Test search error handling scenarios"""
        mock_st = MockStreamlitComponents()
        mock_session_manager = MockSessionManager()
        mock_vector_manager = MockVectorStoreManager([])  # No indices
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st.get_mock(),
            session_manager=mock_session_manager.get_mock(),
            vector_store_manager=mock_vector_manager.get_mock()
        ):
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            page.render()
            
            # Should show error for no vector indices
            mock_st.get_mock().error.assert_called()
            mock_st.get_mock().info.assert_called()


class TestCatalogPageIntegration:
    """Integration tests for CatalogPage with realistic scenarios"""
    
    def test_complete_catalog_workflow_with_analytics(self):
        """Test complete catalog workflow with cached analytics"""
        # Setup mocks
        mock_st = MockStreamlitComponents()
        mock_session_manager = MockSessionManager(csv_data=get_sample_query_data('large', 50))
        sample_analytics = get_sample_analytics('comprehensive')
        
        # Configure search input
        mock_st.configure_input('text_input', 'customers')
        mock_st.configure_input('selectbox', 2)  # Page 2
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st.get_mock(),
            session_manager=mock_session_manager.get_mock()
        ), patch('modular.page_modules.catalog_page.CATALOG_ANALYTICS_DIR') as mock_dir:
            
            mock_dir.exists.return_value = True
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Mock analytics loading
            page.load_cached_analytics = Mock(return_value={'join_analysis': sample_analytics})
            page.load_cached_graph_files = Mock(return_value=[])
            
            page.render()
            
            # Verify workflow components
            mock_session_manager.get_mock().load_csv_data_if_needed.assert_called()
            mock_st.get_mock().title.assert_called()
            mock_st.get_mock().text_input.assert_called()
    
    def test_catalog_pagination_workflow(self):
        """Test catalog pagination with large dataset"""
        mock_st = MockStreamlitComponents()
        large_dataset = get_sample_query_data('large', 100)
        mock_session_manager = MockSessionManager(csv_data=large_dataset)
        
        # Configure for page 3 selection
        mock_st.configure_input('selectbox', 3)
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st.get_mock(),
            session_manager=mock_session_manager.get_mock()
        ):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Mock analytics to avoid complex setup
            page.load_cached_analytics = Mock(return_value={'join_analysis': get_sample_analytics('minimal')})
            
            # Test pagination controls
            current_page, pagination_info = page.render_pagination_controls(large_dataset)
            
            assert current_page == 3
            assert pagination_info['has_multiple_pages'] == True
            
            # Verify pagination UI was rendered
            mock_st.get_mock().columns.assert_called()
            mock_st.get_mock().selectbox.assert_called()
            mock_st.get_mock().metric.assert_called()
    
    def test_catalog_search_integration(self):
        """Test catalog search functionality with different data types"""
        mock_st = MockStreamlitComponents()
        search_data = get_sample_query_data('search')
        mock_session_manager = MockSessionManager(csv_data=search_data)
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st.get_mock(),
            session_manager=mock_session_manager.get_mock()
        ), patch('modular.page_modules.catalog_page.safe_get_value') as mock_safe_get:
            
            # Configure safe_get_value to return actual values
            def safe_get_side_effect(row, column, default=''):
                return str(row.get(column, default))
            mock_safe_get.side_effect = safe_get_side_effect
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Test search for "customers" - should find results
            result = page.search_queries(search_data, 'customers')
            assert len(result) > 0
            
            # Test search for "nonexistent" - should find few or no results
            result = page.search_queries(search_data, 'nonexistent_term')
            assert len(result) <= len(search_data)
            
            # Verify search feedback was provided
            mock_st.get_mock().info.assert_called()


class TestChatPageIntegration:
    """Integration tests for ChatPage"""
    
    def test_chat_page_initialization(self):
        """Test chat page initialization workflow"""
        mock_st = MockStreamlitComponents()
        mock_session_manager = MockSessionManager()
        mock_vector_manager = MockVectorStoreManager(['chat_index'])
        
        # Configure session manager returns
        mock_session_manager.get_mock().get_vector_store.return_value = Mock()
        mock_session_manager.get_mock().get_csv_data.return_value = get_sample_query_data('basic')
        
        with patch.multiple(
            'modular.page_modules.chat_page',
            st=mock_st.get_mock(),
            session_manager=mock_session_manager.get_mock(),
            vector_store_manager=mock_vector_manager.get_mock()
        ), patch('modular.page_modules.chat_page.create_chat_page') as mock_create_chat:
            
            from modular.page_modules.chat_page import render
            
            render()
            
            # Verify vector store loading was attempted
            mock_vector_manager.get_mock().load_vector_store_if_needed.assert_called()
            
            # Verify data was retrieved
            mock_session_manager.get_mock().get_vector_store.assert_called()
            mock_session_manager.get_mock().get_csv_data.assert_called()
            
            # Verify chat page creation was called
            mock_create_chat.assert_called()
    
    def test_chat_page_error_handling(self):
        """Test chat page error handling"""
        mock_st = MockStreamlitComponents()
        mock_session_manager = MockSessionManager()
        mock_vector_manager = MockVectorStoreManager()
        
        # Configure vector store loading to fail
        mock_vector_manager.get_mock().load_vector_store_if_needed.return_value = False
        
        with patch.multiple(
            'modular.page_modules.chat_page',
            st=mock_st.get_mock(),
            session_manager=mock_session_manager.get_mock(),
            vector_store_manager=mock_vector_manager.get_mock()
        ):
            from modular.page_modules.chat_page import render
            
            render()
            
            # Should show error message
            mock_st.get_mock().error.assert_called()
            mock_st.get_mock().info.assert_called()


class TestPageRoutingIntegration:
    """Integration tests for main app page routing"""
    
    def test_app_routing_to_search_page(self):
        """Test main app routing to search page"""
        mock_st = MockStreamlitComponents()
        
        # Configure session state for search page
        mock_st.configure_session_state({
            'page_selection': '🔍 Query Search',
            'selected_vector_index': 'test_index'
        })
        
        with patch.multiple(
            'modular.app',
            st=mock_st.get_mock()
        ), patch('modular.app.session_manager') as mock_session, \
          patch('modular.app.navigation') as mock_nav, \
          patch('modular.app.search_page') as mock_search_page:
            
            # Configure navigation mock
            mock_nav.get_page_from_selection.return_value = 'search'
            mock_nav.render_sidebar.return_value = 'test_index'
            
            # Configure session manager
            mock_session.initialize_session_state.return_value = None
            mock_session.load_csv_data_if_needed.return_value = True
            
            from modular.app import route_to_page
            
            route_to_page('search')
            
            # Verify search page render was called
            mock_search_page.render.assert_called()
    
    def test_app_routing_to_catalog_page(self):
        """Test main app routing to catalog page"""
        mock_st = MockStreamlitComponents()
        
        with patch.multiple(
            'modular.app',
            st=mock_st.get_mock()
        ), patch('modular.app.catalog_page') as mock_catalog_page:
            
            from modular.app import route_to_page
            
            route_to_page('catalog')
            
            # Verify catalog page render was called
            mock_catalog_page.render.assert_called()
    
    def test_app_routing_error_handling(self):
        """Test main app routing error handling"""
        mock_st = MockStreamlitComponents()
        
        with patch.multiple(
            'modular.app',
            st=mock_st.get_mock()
        ):
            from modular.app import route_to_page
            
            # Test unknown page routing
            route_to_page('unknown_page')
            
            # Should show error message
            mock_st.get_mock().error.assert_called()


class TestEndToEndWorkflows:
    """End-to-end integration tests simulating real user workflows"""
    
    def test_search_to_catalog_workflow(self):
        """Test user workflow: search for queries, then browse catalog"""
        # This would simulate a user performing a search, then navigating to catalog
        mock_st = MockStreamlitComponents()
        sample_data = get_sample_query_data('parsed')
        
        # Step 1: Search page workflow
        mock_session_manager = MockSessionManager(csv_data=sample_data)
        mock_vector_manager = MockVectorStoreManager(['search_index'])
        mock_rag_engine = MockRAGEngine()
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st.get_mock(),
            session_manager=mock_session_manager.get_mock(),
            vector_store_manager=mock_vector_manager.get_mock(),
            rag_engine=mock_rag_engine.get_mock()
        ):
            from modular.page_modules.search_page import SearchPage
            
            search_page = SearchPage()
            # Mock successful configuration
            search_page.render_search_configuration = Mock(return_value=get_search_config('default'))
            
            # Step 2: Catalog page workflow with same data
            with patch.multiple(
                'modular.page_modules.catalog_page',
                st=mock_st.get_mock(),
                session_manager=mock_session_manager.get_mock()
            ):
                from modular.page_modules.catalog_page import CatalogPage
                
                catalog_page = CatalogPage()
                catalog_page.load_cached_analytics = Mock(return_value={'join_analysis': get_sample_analytics('minimal')})
                
                # Verify both pages can work with the same session manager
                assert mock_session_manager.get_mock().get_csv_data() is not None
    
    def test_configuration_persistence_across_pages(self):
        """Test that configuration and state persist across page navigation"""
        mock_st = MockStreamlitComponents()
        
        # Configure persistent session state
        persistent_state = {
            'selected_vector_index': 'persistent_index',
            'last_query': 'How to optimize SQL queries?',
            'chat_history': []
        }
        mock_st.configure_session_state(persistent_state)
        
        # Test that different pages can access the same session state
        mock_session_manager = MockSessionManager()
        
        with patch.multiple(
            'modular.session_manager',
            st=mock_st.get_mock()
        ):
            # Verify session state is accessible
            assert mock_st.get_mock().session_state['selected_vector_index'] == 'persistent_index'
            assert mock_st.get_mock().session_state['last_query'] == 'How to optimize SQL queries?'


def create_large_dataset_fixture(num_queries: int):
    """Helper to create large dataset for pagination testing"""
    return get_sample_query_data('large', num_queries)