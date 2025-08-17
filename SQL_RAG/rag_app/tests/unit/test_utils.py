"""
Unit tests for utility functions in modular.utils
"""
import pytest
import pandas as pd
import math
from unittest.mock import Mock

# Add parent directory to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modular.utils import (
    estimate_token_count,
    calculate_context_utilization,
    safe_get_value,
    calculate_pagination,
    get_page_slice,
    get_page_info,
    format_cost,
    calculate_token_cost,
    validate_query_input,
    clean_agent_indicator,
    parse_json_safely,
    format_number_with_commas,
    truncate_text,
    extract_agent_type,
    is_empty_or_whitespace,
    find_original_queries_for_sources
)


class TestEstimateTokenCount:
    """Test token estimation function"""
    
    def test_empty_string(self):
        assert estimate_token_count("") == 0
    
    def test_short_text(self):
        assert estimate_token_count("test") == 1  # 4 chars = 1 token
    
    def test_longer_text(self):
        assert estimate_token_count("this is a test") == 3  # 14 chars = 3 tokens
    
    def test_exact_multiples(self):
        assert estimate_token_count("1234") == 1
        assert estimate_token_count("12345678") == 2


class TestCalculateContextUtilization:
    """Test context utilization calculation"""
    
    def test_empty_docs(self):
        result = calculate_context_utilization([], "test query")
        assert result['chunks_used'] == 0
        assert result['avg_tokens_per_chunk'] == 0
        assert result['context_tokens'] == 0
    
    def test_single_doc(self):
        mock_doc = Mock()
        mock_doc.page_content = "This is test content"
        
        result = calculate_context_utilization([mock_doc], "test")
        assert result['chunks_used'] == 1
        assert result['query_tokens'] == 1  # "test" = 4 chars = 1 token
        assert result['context_tokens'] == 5  # 20 chars = 5 tokens
        assert result['total_input_tokens'] == 6
    
    def test_multiple_docs(self):
        mock_docs = [Mock(), Mock()]
        mock_docs[0].page_content = "First document content"
        mock_docs[1].page_content = "Second document content"
        
        result = calculate_context_utilization(mock_docs, "query")
        assert result['chunks_used'] == 2
        assert result['avg_tokens_per_chunk'] > 0


class TestSafeGetValue:
    """Test safe value extraction from DataFrame rows"""
    
    def test_normal_value(self):
        row = {'column1': 'value1', 'column2': 'value2'}
        assert safe_get_value(row, 'column1') == 'value1'
    
    def test_missing_column(self):
        row = {'column1': 'value1'}
        assert safe_get_value(row, 'missing_col') == ''
        assert safe_get_value(row, 'missing_col', 'default') == 'default'
    
    def test_none_value(self):
        row = {'column1': None}
        assert safe_get_value(row, 'column1') == ''
    
    def test_nan_value(self):
        row = {'column1': pd.NA}
        assert safe_get_value(row, 'column1') == ''
    
    def test_strips_whitespace(self):
        row = {'column1': '  value  '}
        assert safe_get_value(row, 'column1') == 'value'


class TestCalculatePagination:
    """Test pagination calculations"""
    
    def test_empty_data(self):
        result = calculate_pagination(0)
        assert result['total_pages'] == 0
        assert result['has_multiple_pages'] == False
        assert result['total_queries'] == 0
    
    def test_single_page(self):
        result = calculate_pagination(10, page_size=15)
        assert result['total_pages'] == 1
        assert result['has_multiple_pages'] == False
        assert result['total_queries'] == 10
    
    def test_multiple_pages(self):
        result = calculate_pagination(25, page_size=10)
        assert result['total_pages'] == 3
        assert result['has_multiple_pages'] == True
        assert result['total_queries'] == 25
    
    def test_exact_page_boundary(self):
        result = calculate_pagination(30, page_size=15)
        assert result['total_pages'] == 2
        assert result['has_multiple_pages'] == True


class TestGetPageSlice:
    """Test DataFrame page slicing"""
    
    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = get_page_slice(df, 1)
        assert result.empty
    
    def test_invalid_page_number(self):
        df = pd.DataFrame({'col': [1, 2, 3]})
        result = get_page_slice(df, 0)
        assert result.empty
    
    def test_page_beyond_data(self):
        df = pd.DataFrame({'col': [1, 2, 3]})
        result = get_page_slice(df, 5, page_size=10)
        assert result.empty
    
    def test_first_page(self):
        df = pd.DataFrame({'col': list(range(25))})
        result = get_page_slice(df, 1, page_size=10)
        assert len(result) == 10
        assert result.iloc[0]['col'] == 0
        assert result.iloc[9]['col'] == 9
    
    def test_middle_page(self):
        df = pd.DataFrame({'col': list(range(25))})
        result = get_page_slice(df, 2, page_size=10)
        assert len(result) == 10
        assert result.iloc[0]['col'] == 10
        assert result.iloc[9]['col'] == 19
    
    def test_last_page_partial(self):
        df = pd.DataFrame({'col': list(range(25))})
        result = get_page_slice(df, 3, page_size=10)
        assert len(result) == 5
        assert result.iloc[0]['col'] == 20
        assert result.iloc[4]['col'] == 24


class TestGetPageInfo:
    """Test page information calculation"""
    
    def test_first_page(self):
        result = get_page_info(1, 100, page_size=10)
        assert result['start_query'] == 1
        assert result['end_query'] == 10
        assert result['queries_on_page'] == 10
    
    def test_middle_page(self):
        result = get_page_info(3, 100, page_size=10)
        assert result['start_query'] == 21
        assert result['end_query'] == 30
        assert result['queries_on_page'] == 10
    
    def test_last_page_partial(self):
        result = get_page_info(3, 25, page_size=10)
        assert result['start_query'] == 21
        assert result['end_query'] == 25
        assert result['queries_on_page'] == 5


class TestFormatCost:
    """Test cost formatting"""
    
    def test_very_small_cost(self):
        assert format_cost(0.0005) == "$0.500m"
    
    def test_small_cost(self):
        assert format_cost(0.0123) == "$0.0123"
    
    def test_large_cost(self):
        assert format_cost(1.234) == "$1.23"
    
    def test_zero_cost(self):
        assert format_cost(0) == "$0.000m"


class TestCalculateTokenCost:
    """Test token cost calculation"""
    
    def test_known_model(self):
        token_costs = {'test-model': {'input': 0.001, 'output': 0.002}}
        cost = calculate_token_cost(1000, 500, 'test-model', token_costs)
        expected = (1000/1000 * 0.001) + (500/1000 * 0.002)  # 0.001 + 0.001 = 0.002
        assert cost == expected
    
    def test_unknown_model(self):
        token_costs = {'test-model': {'input': 0.001, 'output': 0.002}}
        cost = calculate_token_cost(1000, 500, 'unknown-model', token_costs)
        assert cost == 0.0


class TestValidateQueryInput:
    """Test query input validation"""
    
    def test_empty_query(self):
        is_valid, msg = validate_query_input("")
        assert not is_valid
        assert "enter a question" in msg.lower()
    
    def test_whitespace_only(self):
        is_valid, msg = validate_query_input("   ")
        assert not is_valid
        assert "enter a question" in msg.lower()
    
    def test_too_short(self):
        is_valid, msg = validate_query_input("hi")
        assert not is_valid
        assert "too short" in msg.lower()
    
    def test_too_long(self):
        long_query = "x" * 1001
        is_valid, msg = validate_query_input(long_query)
        assert not is_valid
        assert "too long" in msg.lower()
    
    def test_valid_query(self):
        is_valid, msg = validate_query_input("How do I calculate customer lifetime value?")
        assert is_valid
        assert msg == ""


class TestCleanAgentIndicator:
    """Test agent indicator cleaning"""
    
    def test_explain_indicator(self):
        result = clean_agent_indicator("@explain How does this work?")
        assert result == "How does this work?"
    
    def test_create_indicator(self):
        result = clean_agent_indicator("@create a new query for sales")
        assert result == "a new query for sales"
    
    def test_longanswer_indicator(self):
        result = clean_agent_indicator("Please @longanswer this question")
        assert result == "Please this question"
    
    def test_no_indicators(self):
        result = clean_agent_indicator("Regular question")
        assert result == "Regular question"
    
    def test_multiple_spaces(self):
        result = clean_agent_indicator("@explain   multiple    spaces")
        assert result == "multiple spaces"


class TestParseJsonSafely:
    """Test safe JSON parsing"""
    
    def test_valid_json(self):
        result = parse_json_safely('{"key": "value"}')
        assert result == {"key": "value"}
    
    def test_invalid_json(self):
        result = parse_json_safely('{invalid json}')
        assert result == []
    
    def test_empty_string(self):
        result = parse_json_safely('')
        assert result == []
    
    def test_none_value(self):
        result = parse_json_safely(None)
        assert result == []
    
    def test_custom_default(self):
        result = parse_json_safely('{invalid}', default={'error': True})
        assert result == {'error': True}


class TestFormatNumberWithCommas:
    """Test number formatting with commas"""
    
    def test_small_number(self):
        assert format_number_with_commas(123) == "123"
    
    def test_thousands(self):
        assert format_number_with_commas(1234) == "1,234"
    
    def test_millions(self):
        assert format_number_with_commas(1234567) == "1,234,567"


class TestTruncateText:
    """Test text truncation"""
    
    def test_short_text(self):
        result = truncate_text("short", 10)
        assert result == "short"
    
    def test_exact_length(self):
        result = truncate_text("exactly10c", 10)
        assert result == "exactly10c"
    
    def test_long_text(self):
        result = truncate_text("this is a very long text", 10)
        assert result == "this is..."
    
    def test_custom_suffix(self):
        result = truncate_text("long text", 8, suffix=">>")
        assert result == "long t>>"


class TestExtractAgentType:
    """Test agent type extraction"""
    
    def test_explain_agent(self):
        agent_type, cleaned = extract_agent_type("@explain How does this work?")
        assert agent_type == "explain"
        assert cleaned == "How does this work?"
    
    def test_create_agent(self):
        agent_type, cleaned = extract_agent_type("@create a new SQL query")
        assert agent_type == "create"
        assert cleaned == "a new SQL query"
    
    def test_longanswer_agent(self):
        agent_type, cleaned = extract_agent_type("Please @longanswer this question")
        assert agent_type == "longanswer"
        assert cleaned == "Please this question"
    
    def test_no_agent(self):
        agent_type, cleaned = extract_agent_type("Regular question")
        assert agent_type is None
        assert cleaned == "Regular question"
    
    def test_case_insensitive(self):
        agent_type, cleaned = extract_agent_type("@EXPLAIN test")
        assert agent_type == "explain"
        assert cleaned == "test"


class TestIsEmptyOrWhitespace:
    """Test empty/whitespace detection"""
    
    def test_none_value(self):
        assert is_empty_or_whitespace(None) == True
    
    def test_empty_string(self):
        assert is_empty_or_whitespace("") == True
    
    def test_whitespace_only(self):
        assert is_empty_or_whitespace("   ") == True
    
    def test_pandas_na(self):
        assert is_empty_or_whitespace(pd.NA) == True
    
    def test_valid_string(self):
        assert is_empty_or_whitespace("hello") == False
    
    def test_non_string(self):
        assert is_empty_or_whitespace(123) == False


class TestFindOriginalQueriesForSources:
    """Test source-to-query mapping"""
    
    def test_empty_sources(self):
        df = pd.DataFrame({'query': ['test query']})
        result = find_original_queries_for_sources([], df)
        assert result == []
    
    def test_empty_dataframe(self):
        mock_doc = Mock()
        mock_doc.page_content = "test content"
        result = find_original_queries_for_sources([mock_doc], pd.DataFrame())
        assert result == []
    
    def test_exact_match(self):
        df = pd.DataFrame({
            'query': ['SELECT * FROM customers', 'SELECT * FROM orders'],
            'description': ['Get all customers', 'Get all orders']
        })
        
        mock_doc = Mock()
        mock_doc.page_content = "SELECT * FROM customers"
        
        result = find_original_queries_for_sources([mock_doc], df)
        assert len(result) == 1
        assert result[0]['query'] == 'SELECT * FROM customers'
    
    def test_partial_match(self):
        df = pd.DataFrame({
            'query': ['SELECT customer_id, name FROM customers WHERE city = "NYC"'],
            'description': ['NYC customers']
        })
        
        mock_doc = Mock()
        mock_doc.page_content = "FROM customers WHERE city"
        
        result = find_original_queries_for_sources([mock_doc], df)
        assert len(result) == 1
    
    def test_no_match(self):
        df = pd.DataFrame({
            'query': ['SELECT * FROM customers'],
            'description': ['Get customers']
        })
        
        mock_doc = Mock()
        mock_doc.page_content = "completely different content"
        
        result = find_original_queries_for_sources([mock_doc], df)
        assert result == []
    
    def test_duplicate_filtering(self):
        df = pd.DataFrame({
            'query': ['SELECT * FROM customers'] * 3,
            'description': ['Get customers'] * 3
        })
        
        mock_docs = [Mock(), Mock()]
        mock_docs[0].page_content = "SELECT * FROM customers"
        mock_docs[1].page_content = "SELECT * FROM customers"
        
        result = find_original_queries_for_sources(mock_docs, df)
        assert len(result) == 1  # Should deduplicate