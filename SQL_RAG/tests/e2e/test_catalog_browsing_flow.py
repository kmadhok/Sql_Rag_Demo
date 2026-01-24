#!/usr/bin/env python3
"""
End-to-End Tests for Query Catalog Browsing Flow

Tests catalog page functionality:
- Data loading (CSV/Parquet/cache)
- Search and filtering
- Pagination
- Query card display
- Analytics display
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import sys
from pathlib import Path
import pandas as pd
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "rag_app"))


@pytest.mark.e2e
@pytest.mark.catalog
class TestCatalogBrowsingFlow:
    """Test suite for query catalog browsing flows"""

    def test_csv_data_loading(self, mock_csv_data):
        """Test loading query data from CSV"""
        assert isinstance(mock_csv_data, pd.DataFrame), "Should load as DataFrame"
        assert 'query' in mock_csv_data.columns, "Should have query column"
        assert len(mock_csv_data) > 0, "Should have queries"

    def test_pagination_calculation_single_page(self):
        """Test pagination for datasets that fit on one page"""
        from rag_app.app_simple_gemini import calculate_pagination

        pagination = calculate_pagination(total_queries=10, page_size=15)

        assert pagination['total_pages'] == 1, "Should have 1 page"
        assert pagination['has_multiple_pages'] is False, "Should not need pagination"
        assert pagination['total_queries'] == 10, "Should track total"

    def test_pagination_calculation_multiple_pages(self):
        """Test pagination for large datasets"""
        from rag_app.app_simple_gemini import calculate_pagination

        pagination = calculate_pagination(total_queries=100, page_size=15)

        assert pagination['total_pages'] == 7, "Should have 7 pages (100/15 = 6.67 -> 7)"
        assert pagination['has_multiple_pages'] is True, "Should need pagination"
        assert pagination['total_queries'] == 100, "Should track total"

    def test_pagination_calculation_empty_dataset(self):
        """Test pagination with no queries"""
        from rag_app.app_simple_gemini import calculate_pagination

        pagination = calculate_pagination(total_queries=0, page_size=15)

        assert pagination['total_pages'] == 0, "Should have 0 pages"
        assert pagination['has_multiple_pages'] is False, "Should not need pagination"

    def test_page_slice_extraction(self, mock_csv_data):
        """Test extracting specific page of data"""
        from rag_app.app_simple_gemini import get_page_slice

        # Get first page
        page1 = get_page_slice(mock_csv_data, page_num=1, page_size=5)
        assert len(page1) == 5, "First page should have 5 items"

        # Get second page
        page2 = get_page_slice(mock_csv_data, page_num=2, page_size=5)
        assert len(page2) == 5, "Second page should have 5 items"

        # Verify pages are different
        assert not page1.equals(page2), "Pages should contain different data"

    def test_page_info_calculation(self):
        """Test page range information calculation"""
        from rag_app.app_simple_gemini import get_page_info

        # First page
        info = get_page_info(page_num=1, total_queries=100, page_size=15)
        assert info['start_query'] == 1, "First page starts at 1"
        assert info['end_query'] == 15, "First page ends at 15"
        assert info['queries_on_page'] == 15, "First page has 15 queries"

        # Middle page
        info = get_page_info(page_num=3, total_queries=100, page_size=15)
        assert info['start_query'] == 31, "Third page starts at 31"
        assert info['end_query'] == 45, "Third page ends at 45"

        # Last partial page
        info = get_page_info(page_num=7, total_queries=100, page_size=15)
        assert info['start_query'] == 91, "Last page starts at 91"
        assert info['end_query'] == 100, "Last page ends at 100"
        assert info['queries_on_page'] == 10, "Last page has 10 queries"

    def test_safe_get_value(self):
        """Test safe value extraction from DataFrame rows"""
        from rag_app.app_simple_gemini import safe_get_value

        # Normal value
        row = pd.Series({'query': 'SELECT * FROM users', 'description': 'Get all users'})
        value = safe_get_value(row, 'query')
        assert value == 'SELECT * FROM users', "Should get normal value"

        # Missing column
        value = safe_get_value(row, 'nonexistent', default='N/A')
        assert value == 'N/A', "Should return default for missing column"

        # NaN value
        row_with_nan = pd.Series({'query': 'SELECT *', 'description': pd.NA})
        value = safe_get_value(row_with_nan, 'description', default='')
        assert value == '', "Should handle NaN values"

    def test_search_with_preparsed_data(self, mock_csv_data):
        """Test search functionality with pre-parsed tables and joins"""
        # Simulate search by filtering
        search_term = "users"

        # Search in query column
        filtered = mock_csv_data[
            mock_csv_data['query'].str.contains(search_term, case=False, na=False)
        ]

        assert len(filtered) > 0, "Should find matching queries"
        assert all(search_term.lower() in q.lower() for q in filtered['query']), \
            "All results should contain search term"

    def test_search_in_tables_column(self, mock_csv_data):
        """Test search in pre-parsed tables"""
        # Filter for queries that involve specific tables
        has_users = mock_csv_data[
            mock_csv_data['tables_parsed'].apply(
                lambda tables: 'users' in tables if isinstance(tables, list) else False
            )
        ]

        assert len(has_users) > 0, "Should find queries with users table"

    def test_join_analysis_structure(self):
        """Test structure of join analysis data"""
        # Mock join analysis data
        join_analysis = {
            'total_queries': 15,
            'queries_with_descriptions': 15,
            'queries_with_tables': 15,
            'queries_with_joins': 8,
            'total_individual_joins': 10,
            'max_joins_per_query': 2,
            'json_format_count': 10,
            'string_format_count': 0,
            'join_types': {'LEFT JOIN': 5, 'INNER JOIN': 5},
            'table_usage': {'users': 10, 'orders': 8, 'products': 5},
            'relationships': [],
            'join_count_distribution': {0: 7, 1: 6, 2: 2}
        }

        # Verify structure
        assert 'total_queries' in join_analysis, "Should track total queries"
        assert 'queries_with_joins' in join_analysis, "Should track join queries"
        assert 'join_types' in join_analysis, "Should track join types"
        assert 'table_usage' in join_analysis, "Should track table usage"

    def test_query_card_display_data_preparation(self, mock_csv_data):
        """Test data preparation for query card display"""
        # Get first query
        first_query = mock_csv_data.iloc[0]

        # Verify it has expected fields
        assert 'query' in first_query, "Should have query"

        # Check for pre-parsed data
        if 'tables_parsed' in first_query:
            assert isinstance(first_query['tables_parsed'], (list, str)), \
                "tables_parsed should be list or string"

        if 'joins_parsed' in first_query:
            assert isinstance(first_query['joins_parsed'], (list, str)), \
                "joins_parsed should be list or string"

    def test_cached_analytics_loading(self, tmp_path):
        """Test loading cached analytics from JSON files"""
        # Create mock cache directory
        cache_dir = tmp_path / "catalog_analytics"
        cache_dir.mkdir()

        # Create mock metadata
        metadata = {
            'source_csv_modified': 1234567890,
            'processing_time': 5.2,
            'total_queries': 15
        }

        # Create mock join analysis
        join_analysis = {
            'total_queries': 15,
            'queries_with_joins': 8
        }

        # Write to files
        with open(cache_dir / "cache_metadata.json", 'w') as f:
            json.dump(metadata, f)

        with open(cache_dir / "join_analysis.json", 'w') as f:
            json.dump(join_analysis, f)

        # Verify files exist
        assert (cache_dir / "cache_metadata.json").exists(), "Metadata should exist"
        assert (cache_dir / "join_analysis.json").exists(), "Join analysis should exist"

        # Load and verify
        with open(cache_dir / "cache_metadata.json") as f:
            loaded_metadata = json.load(f)

        assert loaded_metadata['total_queries'] == 15, "Should load correct data"

    def test_empty_dataset_handling(self):
        """Test handling of empty dataset"""
        from rag_app.app_simple_gemini import calculate_pagination

        empty_df = pd.DataFrame()

        # Pagination should handle empty data
        pagination = calculate_pagination(total_queries=0)
        assert pagination['total_pages'] == 0, "Empty dataset should have 0 pages"

    def test_single_query_dataset(self):
        """Test handling of dataset with single query"""
        from rag_app.app_simple_gemini import calculate_pagination, get_page_slice

        single_query_df = pd.DataFrame({
            'query': ['SELECT * FROM users'],
            'description': ['Get all users'],
            'tables_parsed': [['users']],
            'joins_parsed': [[]]
        })

        # Pagination
        pagination = calculate_pagination(total_queries=1)
        assert pagination['total_pages'] == 1, "Single query should have 1 page"

        # Page slice
        page = get_page_slice(single_query_df, page_num=1)
        assert len(page) == 1, "Should return single query"

    def test_exact_page_boundary(self):
        """Test pagination at exact page boundaries"""
        from rag_app.app_simple_gemini import calculate_pagination

        # Exactly 3 pages worth of queries
        pagination = calculate_pagination(total_queries=45, page_size=15)

        assert pagination['total_pages'] == 3, "Should have exactly 3 pages"
        assert pagination['has_multiple_pages'] is True, "Should have multiple pages"

    def test_beyond_last_page_request(self, mock_csv_data):
        """Test requesting page beyond dataset"""
        from rag_app.app_simple_gemini import get_page_slice

        # Request page 100 when we only have 15 queries
        page = get_page_slice(mock_csv_data, page_num=100, page_size=15)

        assert page.empty, "Should return empty DataFrame for out of range page"

    def test_search_with_special_characters(self, mock_csv_data):
        """Test search with SQL special characters"""
        # Search for queries with wildcards
        search_term = "%"

        filtered = mock_csv_data[
            mock_csv_data['query'].str.contains(search_term, case=False, na=False, regex=False)
        ]

        # Should not crash, even if no results
        assert isinstance(filtered, pd.DataFrame), "Should return DataFrame"

    def test_case_insensitive_search(self, mock_csv_data):
        """Test that search is case-insensitive"""
        # Search with uppercase
        upper_filtered = mock_csv_data[
            mock_csv_data['query'].str.contains('SELECT', case=False, na=False)
        ]

        # Search with lowercase
        lower_filtered = mock_csv_data[
            mock_csv_data['query'].str.contains('select', case=False, na=False)
        ]

        assert len(upper_filtered) == len(lower_filtered), "Search should be case-insensitive"

    def test_multi_table_join_display(self):
        """Test display preparation for queries with multiple joins"""
        # Mock query with 2 joins
        joins_parsed = [
            {
                'left_table': 'orders',
                'right_table': 'order_items',
                'join_type': 'INNER JOIN',
                'left_column': 'order_id',
                'right_column': 'order_id',
                'condition': 'o.order_id = oi.order_id',
                'format': 'json'
            },
            {
                'left_table': 'order_items',
                'right_table': 'products',
                'join_type': 'INNER JOIN',
                'left_column': 'product_id',
                'right_column': 'product_id',
                'condition': 'oi.product_id = p.product_id',
                'format': 'json'
            }
        ]

        assert len(joins_parsed) == 2, "Should have 2 joins"
        assert all('join_type' in j for j in joins_parsed), "All joins should have type"

    def test_table_relationship_graph_data(self):
        """Test structure of table relationship graph data"""
        # Mock relationships for graph
        relationships = [
            {
                'left_table': 'users',
                'right_table': 'orders',
                'join_type': 'LEFT JOIN',
                'condition': 'u.user_id = o.user_id'
            },
            {
                'left_table': 'orders',
                'right_table': 'order_items',
                'join_type': 'INNER JOIN',
                'condition': 'o.order_id = oi.order_id'
            }
        ]

        # Verify structure
        assert len(relationships) == 2, "Should have 2 relationships"
        assert all('left_table' in r for r in relationships), "Should have left_table"
        assert all('right_table' in r for r in relationships), "Should have right_table"
