"""
Unit tests for SearchPage specific functionality
"""
import pytest
from unittest.mock import patch, Mock, MagicMock

# Add parent directory to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import test helpers
from tests.mock_helpers import (
    MockStreamlitComponents, 
    MockVectorStoreManager, 
    create_sample_dataframe,
    MockDocuments
)


class TestSearchPageConfiguration:
    """Test SearchPage configuration rendering and logic"""
    
    def test_render_search_configuration_no_indices(self):
        """Test configuration rendering when no vector indices are available"""
        mock_st = MockStreamlitComponents().get_mock()
        mock_vector_manager = MockVectorStoreManager()
        mock_vector_manager.set_available_indices([])  # No indices available
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st,
            vector_store_manager=mock_vector_manager.get_mock()
        ):
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            result = page.render_search_configuration()
            
            # Should return None when no indices available
            assert result is None
            
            # Should show error message
            mock_st.error.assert_called()
            mock_st.info.assert_called()
    
    def test_render_search_configuration_with_indices(self):
        """Test configuration rendering with available indices"""
        mock_st = MockStreamlitComponents().get_mock()
        mock_vector_manager = MockVectorStoreManager()
        mock_vector_manager.set_available_indices(['index1', 'index2'])
        
        # Configure streamlit inputs to return specific values
        mock_st.selectbox.return_value = 'index1'
        mock_st.slider.return_value = 5
        mock_st.checkbox.side_effect = [True, False, True, False, True, False, True]  # Various checkboxes
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st,
            vector_store_manager=mock_vector_manager.get_mock(),
            HYBRID_SEARCH_AVAILABLE=True
        ):
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            result = page.render_search_configuration()
            
            # Should return configuration dictionary
            assert result is not None
            assert isinstance(result, dict)
            
            # Check expected keys are present
            expected_keys = [
                'selected_index', 'k', 'gemini_mode', 'schema_injection',
                'show_full_queries', 'query_rewriting', 'hybrid_search',
                'auto_adjust_weights'
            ]
            for key in expected_keys:
                assert key in result
            
            # Check specific values based on our mock configuration
            assert result['selected_index'] == 'index1'
            assert result['k'] == 5
            assert result['gemini_mode'] == True  # First checkbox
            assert result['schema_injection'] == False  # Second checkbox
    
    def test_render_search_configuration_without_hybrid_search(self):
        """Test configuration when hybrid search is not available"""
        mock_st = MockStreamlitComponents().get_mock()
        mock_vector_manager = MockVectorStoreManager()
        
        mock_st.selectbox.return_value = 'index1'
        mock_st.slider.return_value = 3
        mock_st.checkbox.return_value = False
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st,
            vector_store_manager=mock_vector_manager.get_mock(),
            HYBRID_SEARCH_AVAILABLE=False
        ):
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            result = page.render_search_configuration()
            
            # Hybrid search should be disabled
            assert result['hybrid_search'] == False
            assert result['search_weights'] is None
            
            # Should show warning about hybrid search not available
            mock_st.caption.assert_called()


class TestSearchPageQueryCardDisplay:
    """Test SearchPage query card display functionality"""
    
    def test_display_query_card_with_parsed_data(self):
        """Test query card display with pre-parsed table and join data"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st
        ), patch('modular.page_modules.search_page.safe_get_value') as mock_safe_get:
            # Configure safe_get_value mock
            def safe_get_side_effect(row, column, default=''):
                return row.get(column, default)
            mock_safe_get.side_effect = safe_get_side_effect
            
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            
            # Test row with parsed data
            test_row = {
                'query': 'SELECT p.name, c.category FROM products p JOIN categories c ON p.category_id = c.id',
                'description': 'Get product names with categories',
                'tables_parsed': ['products', 'categories'],
                'joins_parsed': [
                    {
                        'left_table': 'products',
                        'right_table': 'categories',
                        'join_type': 'INNER JOIN'
                    }
                ]
            }
            
            page.display_query_card(test_row, 0)
            
            # Verify streamlit components were called appropriately
            mock_st.container.assert_called()
            mock_st.expander.assert_called()
            mock_st.code.assert_called_with(test_row['query'], language="sql")
            mock_st.columns.assert_called()
            mock_st.markdown.assert_called()
            mock_st.caption.assert_called()
    
    def test_display_query_card_with_raw_data(self):
        """Test query card display with raw CSV data (fallback)"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st
        ), patch('modular.page_modules.search_page.safe_get_value') as mock_safe_get:
            # Configure safe_get_value mock
            def safe_get_side_effect(row, column, default=''):
                return row.get(column, default)
            mock_safe_get.side_effect = safe_get_side_effect
            
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            
            # Test row with raw data (no parsed columns)
            test_row = {
                'query': 'SELECT * FROM customers',
                'description': 'Get all customers',
                'tables': 'customers, orders',
                'joins': 'customers.id = orders.customer_id'
            }
            
            page.display_query_card(test_row, 0)
            
            # Verify basic components were called
            mock_st.container.assert_called()
            mock_st.expander.assert_called()
            mock_st.code.assert_called_with(test_row['query'], language="sql")


class TestSearchPageResultsDisplay:
    """Test SearchPage results display functionality"""
    
    def test_render_search_results_basic(self):
        """Test basic search results rendering"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st
        ):
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            
            # Mock search results
            answer = "This is a sample answer from the RAG system"
            sources = MockDocuments.create_documents_list([
                "Sample source content 1",
                "Sample source content 2"
            ])
            token_usage = {
                'total_tokens': 150,
                'prompt_tokens': 100,
                'completion_tokens': 50
            }
            config = {
                'gemini_mode': True,
                'show_full_queries': False
            }
            
            page.render_search_results(answer, sources, token_usage, config)
            
            # Verify answer section was rendered
            mock_st.subheader.assert_called()
            mock_st.write.assert_called_with(answer)
            
            # Verify divider was called for sections
            mock_st.divider.assert_called()
    
    def test_display_context_utilization(self):
        """Test context utilization display"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st
        ), patch('modular.page_modules.search_page.calculate_context_utilization') as mock_calc:
            # Mock context utilization calculation
            mock_calc.return_value = {
                'utilization_percent': 25.5,
                'total_input_tokens': 255000,
                'chunks_used': 5,
                'avg_tokens_per_chunk': 100
            }
            
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            
            sources = MockDocuments.create_documents_list(["Sample content"] * 5)
            query = "test query"
            
            page.display_context_utilization(sources, query)
            
            # Verify components were called
            mock_st.subheader.assert_called()
            mock_st.progress.assert_called()
            mock_st.columns.assert_called()
            mock_st.metric.assert_called()
            mock_st.caption.assert_called()
    
    def test_display_sources_chunk_mode(self):
        """Test source display in chunk mode"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st
        ):
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            
            sources = MockDocuments.create_documents_list([
                "First chunk content",
                "Second chunk content"
            ], [
                {'source': 'query1.sql', 'description': 'First query'},
                {'source': 'query2.sql', 'description': 'Second query'}
            ])
            
            config = {'show_full_queries': False}
            
            page.display_sources(sources, config)
            
            # Verify chunk display was used
            mock_st.subheader.assert_called()
            mock_st.caption.assert_called()
            mock_st.expander.assert_called()
            mock_st.code.assert_called()


class TestSearchPageValidation:
    """Test SearchPage input validation and error handling"""
    
    def test_render_instructions(self):
        """Test instructions rendering"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st
        ):
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            page.render_instructions()
            
            # Verify markdown was called to display instructions
            mock_st.markdown.assert_called()
            
            # Check that the markdown call contains helpful content
            call_args = mock_st.markdown.call_args[0][0]
            assert "How to use:" in call_args
            assert "@explain" in call_args
            assert "@create" in call_args
            assert "example questions" in call_args.lower()


class TestSearchPageIntegration:
    """Test SearchPage integration scenarios"""
    
    def test_render_with_missing_csv_data(self):
        """Test render method when CSV data is not available"""
        mock_st = MockStreamlitComponents().get_mock()
        mock_session_manager = Mock()
        mock_session_manager.load_csv_data_if_needed.return_value = False
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st,
            session_manager=mock_session_manager
        ):
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            result = page.render()
            
            # Should return early when CSV data loading fails
            mock_session_manager.load_csv_data_if_needed.assert_called_once()
            # Render should stop early, so title should be called but configuration shouldn't
            mock_st.title.assert_called()
    
    def test_render_with_vector_store_loading_failure(self):
        """Test render method when vector store loading fails"""
        mock_st = MockStreamlitComponents().get_mock()
        mock_session_manager = Mock()
        mock_session_manager.load_csv_data_if_needed.return_value = True
        mock_session_manager.load_schema_manager_if_needed.return_value = None
        
        mock_vector_manager = MockVectorStoreManager()
        mock_vector_manager.get_mock().ensure_vector_store_loaded.return_value = False
        
        # Mock the configuration to return valid config
        mock_config = {
            'selected_index': 'test_index',
            'k': 4,
            'gemini_mode': True,
            'schema_injection': False,
            'show_full_queries': False,
            'query_rewriting': False,
            'hybrid_search': False,
            'auto_adjust_weights': False,
            'search_weights': None
        }
        
        with patch.multiple(
            'modular.page_modules.search_page',
            st=mock_st,
            session_manager=mock_session_manager,
            vector_store_manager=mock_vector_manager.get_mock()
        ):
            from modular.page_modules.search_page import SearchPage
            
            page = SearchPage()
            
            # Mock render_search_configuration to return valid config
            page.render_search_configuration = Mock(return_value=mock_config)
            
            page.render()
            
            # Should attempt to load vector store
            mock_vector_manager.get_mock().ensure_vector_store_loaded.assert_called_once_with('test_index')
            
            # Should display session stats despite vector store failure
            mock_session_manager.display_session_stats.assert_called_once()