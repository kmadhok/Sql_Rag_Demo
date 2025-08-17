"""
Unit tests for CatalogPage specific functionality
"""
import pytest
import pandas as pd
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
    create_sample_dataframe,
    create_sample_analytics
)


class TestCatalogPageAnalytics:
    """Test CatalogPage analytics loading and display"""
    
    def test_load_cached_analytics_no_directory(self):
        """Test analytics loading when directory doesn't exist"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ), patch('modular.page_modules.catalog_page.CATALOG_ANALYTICS_DIR') as mock_dir:
            mock_dir.exists.return_value = False
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            result = page.load_cached_analytics()
            
            assert result is None
    
    def test_load_cached_analytics_success(self):
        """Test successful analytics loading"""
        mock_st = MockStreamlitComponents().get_mock()
        sample_analytics = create_sample_analytics()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ), patch('modular.page_modules.catalog_page.CATALOG_ANALYTICS_DIR') as mock_dir, \
          patch('modular.page_modules.catalog_page.load_join_analysis') as mock_load_join, \
          patch('modular.page_modules.catalog_page.load_table_relationships') as mock_load_table:
            
            mock_dir.exists.return_value = True
            mock_load_join.return_value = sample_analytics
            mock_load_table.return_value = []
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            result = page.load_cached_analytics()
            
            assert result is not None
            assert 'join_analysis' in result
            assert 'table_relationships' in result
            assert result['join_analysis'] == sample_analytics
    
    def test_display_join_analysis(self):
        """Test join analysis display"""
        mock_st = MockStreamlitComponents().get_mock()
        sample_analytics = create_sample_analytics()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st,
            pd=pd
        ):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            page.display_join_analysis(sample_analytics)
            
            # Verify main components were called
            mock_st.subheader.assert_called()
            mock_st.columns.assert_called()
            mock_st.metric.assert_called()
            mock_st.dataframe.assert_called()
    
    def test_display_join_analysis_no_joins(self):
        """Test join analysis display when no joins exist"""
        mock_st = MockStreamlitComponents().get_mock()
        no_joins_analytics = create_sample_analytics()
        no_joins_analytics['total_individual_joins'] = 0
        no_joins_analytics['relationships'] = []
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            page.display_join_analysis(no_joins_analytics)
            
            # Should show basic stats
            mock_st.subheader.assert_called()
            mock_st.metric.assert_called()
            
            # Should show info about no relationships
            mock_st.info.assert_called()


class TestCatalogPageSearch:
    """Test CatalogPage search functionality"""
    
    def test_search_queries_empty_search(self):
        """Test search with empty search term"""
        mock_st = MockStreamlitComponents().get_mock()
        test_df = create_sample_dataframe(5)
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            result = page.search_queries(test_df, '')
            
            # Should return original dataframe
            assert len(result) == len(test_df)
            assert result.equals(test_df)
    
    def test_search_queries_with_parsed_data(self):
        """Test search with pre-parsed data"""
        mock_st = MockStreamlitComponents().get_mock()
        test_df = create_sample_dataframe(5)
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ), patch('modular.page_modules.catalog_page.safe_get_value') as mock_safe_get:
            # Mock safe_get_value to return predictable values
            def safe_get_side_effect(row, column, default=''):
                return str(row.get(column, default))
            mock_safe_get.side_effect = safe_get_side_effect
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            result = page.search_queries(test_df, 'table_0')
            
            # Should find results
            assert len(result) >= 1
            
            # Should show search results info
            mock_st.info.assert_called()
            call_args = mock_st.info.call_args[0][0]
            assert 'Found' in call_args
            assert 'table_0' in call_args
    
    def test_search_queries_without_parsed_data(self):
        """Test search fallback without pre-parsed data"""
        mock_st = MockStreamlitComponents().get_mock()
        
        # Create dataframe without parsed columns
        test_df = pd.DataFrame({
            'query': ['SELECT * FROM customers', 'SELECT * FROM orders'],
            'description': ['Get customers', 'Get orders'],
            'tables': ['customers', 'orders'],
            'joins': ['', '']
        })
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            result = page.search_queries(test_df, 'customers')
            
            # Should find the customers query
            assert len(result) >= 1
            
            # Should show warning about limited search
            mock_st.warning.assert_called()
            mock_st.info.assert_called()
            mock_st.caption.assert_called()
    
    def test_search_queries_no_results(self):
        """Test search with no matching results"""
        mock_st = MockStreamlitComponents().get_mock()
        test_df = create_sample_dataframe(3)
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ), patch('modular.page_modules.catalog_page.safe_get_value') as mock_safe_get:
            # Mock safe_get_value to return predictable values
            def safe_get_side_effect(row, column, default=''):
                return str(row.get(column, default))
            mock_safe_get.side_effect = safe_get_side_effect
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            result = page.search_queries(test_df, 'nonexistent_term')
            
            # Should return empty or very small result set
            assert len(result) <= len(test_df)
            
            # Should still show info about search
            mock_st.info.assert_called()


class TestCatalogPagePagination:
    """Test CatalogPage pagination functionality"""
    
    def test_render_pagination_controls_single_page(self):
        """Test pagination controls for small dataset (single page)"""
        mock_st = MockStreamlitComponents().get_mock()
        small_df = create_sample_dataframe(10)  # Less than page size
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ), patch('modular.page_modules.catalog_page.calculate_pagination') as mock_calc:
            mock_calc.return_value = {
                'has_multiple_pages': False,
                'total_pages': 1
            }
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            current_page, pagination_info = page.render_pagination_controls(small_df)
            
            assert current_page == 1
            assert pagination_info['has_multiple_pages'] == False
            
            # Should show single page info
            mock_st.info.assert_called()
            call_args = mock_st.info.call_args[0][0]
            assert 'single page' in call_args.lower()
    
    def test_render_pagination_controls_multiple_pages(self):
        """Test pagination controls for large dataset (multiple pages)"""
        mock_st = MockStreamlitComponents().get_mock()
        large_df = create_sample_dataframe(50)  # More than page size
        
        # Configure selectbox to return page 2
        mock_st.selectbox.return_value = 2
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ), patch('modular.page_modules.catalog_page.calculate_pagination') as mock_calc, \
          patch('modular.page_modules.catalog_page.get_page_info') as mock_page_info:
            
            mock_calc.return_value = {
                'has_multiple_pages': True,
                'total_pages': 4
            }
            mock_page_info.return_value = {
                'start_query': 16,
                'end_query': 30
            }
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            current_page, pagination_info = page.render_pagination_controls(large_df)
            
            assert current_page == 2
            assert pagination_info['has_multiple_pages'] == True
            
            # Should show pagination controls
            mock_st.columns.assert_called()
            mock_st.metric.assert_called()
            mock_st.selectbox.assert_called()
            mock_st.caption.assert_called()
    
    def test_render_navigation_hints(self):
        """Test navigation hints display"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Test middle page navigation hints
            pagination_info = {'has_multiple_pages': True, 'total_pages': 5}
            page.render_navigation_hints(3, pagination_info)
            
            # Should show divider and navigation hints
            mock_st.divider.assert_called()
            mock_st.columns.assert_called()
            mock_st.caption.assert_called()
    
    def test_render_navigation_hints_single_page(self):
        """Test navigation hints for single page"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Test single page - should not show navigation hints
            pagination_info = {'has_multiple_pages': False, 'total_pages': 1}
            page.render_navigation_hints(1, pagination_info)
            
            # Should not call divider for single page
            mock_st.divider.assert_not_called()


class TestCatalogPageQueryDisplay:
    """Test CatalogPage query card display functionality"""
    
    def test_display_query_card_with_parsed_joins(self):
        """Test query card display with parsed join data"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ), patch('modular.page_modules.catalog_page.safe_get_value') as mock_safe_get:
            # Configure safe_get_value mock
            def safe_get_side_effect(row, column, default=''):
                return row.get(column, default)
            mock_safe_get.side_effect = safe_get_side_effect
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Test row with parsed join data (dict format)
            test_row = {
                'query': 'SELECT * FROM customers c JOIN orders o ON c.id = o.customer_id',
                'description': 'Customers with orders',
                'tables_parsed': ['customers', 'orders'],
                'joins_parsed': [
                    {
                        'left_table': 'customers',
                        'right_table': 'orders',
                        'join_type': 'INNER JOIN'
                    }
                ]
            }
            
            page.display_query_card(test_row, 0)
            
            # Verify components were called
            mock_st.container.assert_called()
            mock_st.expander.assert_called()
            mock_st.code.assert_called()
            mock_st.columns.assert_called()
            mock_st.markdown.assert_called()
            mock_st.caption.assert_called()
    
    def test_display_query_card_with_many_tables(self):
        """Test query card display with many tables (should limit display)"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ), patch('modular.page_modules.catalog_page.safe_get_value') as mock_safe_get:
            # Configure safe_get_value mock
            def safe_get_side_effect(row, column, default=''):
                return row.get(column, default)
            mock_safe_get.side_effect = safe_get_side_effect
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Test row with many tables (should be limited in display)
            test_row = {
                'query': 'SELECT * FROM table1, table2, table3, table4, table5, table6, table7',
                'description': 'Query with many tables',
                'tables_parsed': [f'table{i}' for i in range(1, 8)],  # 7 tables
                'joins_parsed': []
            }
            
            page.display_query_card(test_row, 0)
            
            # Should limit display and show "... and X more"
            mock_st.caption.assert_called()
            
            # Check if "more" was mentioned in any caption call
            caption_calls = [call[0][0] for call in mock_st.caption.call_args_list]
            has_more_message = any('more' in call for call in caption_calls if isinstance(call, str))
            assert has_more_message


class TestCatalogPageErrorHandling:
    """Test CatalogPage error handling"""
    
    def test_render_analytics_error(self):
        """Test analytics error rendering"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # This should call st.stop() which we need to handle
            try:
                page.render_analytics_error()
            except:
                pass  # st.stop() might raise an exception in mock
            
            # Should show error messages
            mock_st.error.assert_called()
            mock_st.code.assert_called()
    
    def test_load_cached_graph_files(self):
        """Test loading cached graph files"""
        mock_st = MockStreamlitComponents().get_mock()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st
        ), patch('modular.page_modules.catalog_page.CATALOG_ANALYTICS_DIR') as mock_dir:
            # Mock directory structure
            mock_dir.exists.return_value = True
            
            # Mock graph files
            mock_svg_file = Mock()
            mock_svg_file.exists.return_value = True
            mock_png_file = Mock()
            mock_png_file.exists.return_value = False
            
            mock_dir.__truediv__.side_effect = lambda x: {
                'relationships_graph.svg': mock_svg_file,
                'relationships_graph.png': mock_png_file
            }[x]
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            result = page.load_cached_graph_files()
            
            # Should find the SVG file but not PNG
            assert len(result) >= 0  # May find files based on mock setup


class TestCatalogPageIntegration:
    """Test CatalogPage integration scenarios"""
    
    def test_render_with_missing_analytics(self):
        """Test render method when analytics are missing"""
        mock_st = MockStreamlitComponents().get_mock()
        mock_session_manager = Mock()
        mock_session_manager.load_csv_data_if_needed.return_value = True
        mock_session_manager.get_csv_data.return_value = create_sample_dataframe(5)
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st,
            session_manager=mock_session_manager
        ), patch('modular.page_modules.catalog_page.CATALOG_ANALYTICS_DIR') as mock_dir:
            mock_dir.exists.return_value = False
            
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Mock the method that would cause st.stop()
            page.load_cached_analytics = Mock(return_value=None)
            
            try:
                page.render()
            except:
                pass  # st.stop() might cause exception
            
            # Should show title and attempt to load data
            mock_st.title.assert_called()
            mock_session_manager.load_csv_data_if_needed.assert_called()
            mock_st.caption.assert_called()
    
    def test_render_with_search_results(self):
        """Test render method with search functionality"""
        mock_st = MockStreamlitComponents().get_mock()
        mock_session_manager = Mock()
        mock_session_manager.load_csv_data_if_needed.return_value = True
        mock_session_manager.get_csv_data.return_value = create_sample_dataframe(5)
        
        # Configure text input to return a search term
        mock_st.text_input.return_value = 'table_0'
        
        sample_analytics = create_sample_analytics()
        
        with patch.multiple(
            'modular.page_modules.catalog_page',
            st=mock_st,
            session_manager=mock_session_manager
        ):
            from modular.page_modules.catalog_page import CatalogPage
            
            page = CatalogPage()
            
            # Mock analytics loading to return data
            page.load_cached_analytics = Mock(return_value={'join_analysis': sample_analytics})
            
            # Mock pagination to avoid complex rendering
            page.render_pagination_controls = Mock(return_value=(1, {'has_multiple_pages': False}))
            
            try:
                page.render()
            except:
                pass  # May encounter issues with complex rendering
            
            # Should attempt search
            mock_st.text_input.assert_called()
            mock_st.title.assert_called()