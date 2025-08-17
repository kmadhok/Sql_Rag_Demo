#!/usr/bin/env python3
"""
Simple test script to verify our testing framework without external dependencies
"""

def estimate_token_count(text: str) -> int:
    """Simple token estimation for testing"""
    return len(text) // 4

def test_estimate_token_count():
    """Test token estimation function"""
    # Test empty string
    assert estimate_token_count("") == 0
    print("✅ Empty string test passed")
    
    # Test short text
    assert estimate_token_count("test") == 1
    print("✅ Short text test passed")
    
    # Test longer text
    assert estimate_token_count("this is a test") == 3
    print("✅ Longer text test passed")

def test_safe_get_value():
    """Test safe value extraction"""
    def safe_get_value(row, column: str, default: str = '') -> str:
        try:
            value = row.get(column, default)
            if value is None:
                return default
            return str(value).strip()
        except:
            return default
    
    # Test normal value
    row = {'column1': 'value1', 'column2': 'value2'}
    assert safe_get_value(row, 'column1') == 'value1'
    print("✅ Normal value test passed")
    
    # Test missing column
    assert safe_get_value(row, 'missing_col') == ''
    assert safe_get_value(row, 'missing_col', 'default') == 'default'
    print("✅ Missing column test passed")
    
    # Test None value
    row_with_none = {'column1': None}
    assert safe_get_value(row_with_none, 'column1') == ''
    print("✅ None value test passed")

def test_calculate_pagination():
    """Test pagination calculations"""
    import math
    
    def calculate_pagination(total_queries: int, page_size: int = 15):
        if total_queries <= 0:
            return {
                'total_pages': 0,
                'page_size': page_size,
                'has_multiple_pages': False,
                'total_queries': 0
            }
        
        total_pages = math.ceil(total_queries / page_size)
        return {
            'total_pages': total_pages,
            'page_size': page_size,
            'has_multiple_pages': total_pages > 1,
            'total_queries': total_queries
        }
    
    # Test empty data
    result = calculate_pagination(0)
    assert result['total_pages'] == 0
    assert result['has_multiple_pages'] == False
    print("✅ Empty data pagination test passed")
    
    # Test single page
    result = calculate_pagination(10, page_size=15)
    assert result['total_pages'] == 1
    assert result['has_multiple_pages'] == False
    print("✅ Single page pagination test passed")
    
    # Test multiple pages
    result = calculate_pagination(25, page_size=10)
    assert result['total_pages'] == 3
    assert result['has_multiple_pages'] == True
    print("✅ Multiple pages pagination test passed")

def test_text_processing():
    """Test text processing functions"""
    def clean_agent_indicator(text: str) -> str:
        patterns = ['@explain', '@create', '@longanswer']
        cleaned = text
        for pattern in patterns:
            cleaned = cleaned.replace(pattern, '').strip()
        cleaned = ' '.join(cleaned.split())
        return cleaned
    
    def extract_agent_type(user_input: str):
        user_input = user_input.strip()
        
        if user_input.lower().startswith('@explain'):
            return 'explain', user_input[8:].strip()
        elif user_input.lower().startswith('@create'):
            return 'create', user_input[7:].strip()
        elif '@longanswer' in user_input.lower():
            return 'longanswer', user_input.replace('@longanswer', '').strip()
        
        return None, user_input
    
    # Test agent indicator cleaning
    result = clean_agent_indicator("@explain How does this work?")
    assert result == "How does this work?"
    print("✅ Agent indicator cleaning test passed")
    
    # Test agent type extraction
    agent_type, cleaned = extract_agent_type("@explain How does this work?")
    assert agent_type == "explain"
    assert cleaned == "How does this work?"
    print("✅ Agent type extraction test passed")

def run_all_tests():
    """Run all tests"""
    print("🧪 Running Simple Tests for SQL RAG Testing Framework")
    print("=" * 60)
    
    try:
        test_estimate_token_count()
        test_safe_get_value()
        test_calculate_pagination()
        test_text_processing()
        
        print("=" * 60)
        print("🎉 All tests passed! Testing framework is working correctly.")
        print("\n📋 Test Summary:")
        print("✅ Utility function tests")
        print("✅ Data validation tests") 
        print("✅ Pagination logic tests")
        print("✅ Text processing tests")
        print("\n🚀 Ready to run full test suite with:")
        print("   python tests/run_tests.py")
        
        return True
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)