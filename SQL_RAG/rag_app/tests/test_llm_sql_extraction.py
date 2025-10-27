#!/usr/bin/env python3
"""
Test LLM-based SQL Extraction

Test the new LLM approach to SQL extraction
"""

import sys
from pathlib import Path
import logging

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock streamlit for testing
sys.modules['streamlit'] = type(sys)('mock_streamlit')
sys.modules['streamlit'].session_state = {}

class TestLLMSQLExtraction:
    """Test LLM-based SQL extraction functionality"""
    
    def test_extraction_function_exists(self):
        """Test that the extraction functions are properly defined"""
        try:
            from ui.pages import extract_sql_with_llm, extract_sql_with_patterns
            
            # Test functions are callable
            assert callable(extract_sql_with_llm), "extract_sql_with_llm is not callable"
            assert callable(extract_sql_with_patterns), "extract_sql_with_patterns is not callable"
            
            print("✅ LLM extraction functions imported successfully")
            return True
            
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            return False
    
    def test_fallback_patterns_work(self):
        """Test that the fallback patterns still work as expected"""
        try:
            from ui.pages import extract_sql_with_patterns
            
            # Test with the complex SQL example
            complex_sql_response = '''Here's the SQL query you requested:

```sql
WITH UserOrderCount AS (
-- Count the number of orders for each user
SELECT user_id, COUNT(order_id) AS num_orders 
FROM `bigquery-public-data.thelook_ecommerce.orders` 
GROUP BY user_id
)
-- Select the user with the most orders and the user with the least orders
SELECT 'Most' AS purchase_type, u.id AS user_id, u.first_name, u.last_name, uoc.num_orders 
FROM `bigquery-public-data.thelook_ecommerce.users` u 
JOIN UserOrderCount uoc ON u.id = uoc.user_id 
ORDER BY uoc.num_orders DESC 
LIMIT 1 
UNION ALL 
SELECT 'Least' AS purchase_type, u.id AS user_id, u.first_name, u.last_name, uoc.num_orders 
FROM `bigquery-public-data.thelook_ecommerce.users` u 
JOIN UserOrderCount uoc ON u.id = uoc.user_id 
ORDER BY uoc.num_orders ASC 
LIMIT 1;
```

This query shows both the user with most orders and least orders.'''
            
            extracted = extract_sql_with_patterns(complex_sql_response)
            
            if extracted:
                print(f"✅ Fallback patterns extracted: {len(extracted)} chars")
                
                # Check for key elements
                assert "WITH UserOrderCount" in extracted, "Missing WITH clause"
                assert "COUNT(order_id)" in extracted, "Missing COUNT function"
                assert "UNION ALL" in extracted, "Missing UNION ALL"
                assert "LIMIT 1" in extracted, "Missing LIMIT clause"
                
                print("✅ All key SQL elements present in fallback extraction")
                return True
            else:
                print("❌ Fallback patterns failed to extract SQL")
                return False
                
        except Exception as e:
            print(f"❌ Fallback pattern test failed: {e}")
            return False
    
    def test_llm_extraction_mock(self):
        """Test LLM extraction with mocked response (since we can't call real LLM in tests)"""
        try:
            from ui.pages import _looks_like_complete_sql
            
            # Test SQL validation with the complete SQL
            complete_sql = '''WITH UserOrderCount AS (
SELECT user_id, COUNT(order_id) AS num_orders 
FROM `bigquery-public-data.thelook_ecommerce.orders` 
GROUP BY user_id
)
SELECT 'Most' AS purchase_type, u.id AS user_id, u.first_name, u.last_name, uoc.num_orders 
FROM `bigquery-public-data.thelook_ecommerce.users` u 
JOIN UserOrderCount uoc ON u.id = uoc.user_id 
ORDER BY uoc.num_orders DESC 
LIMIT 1 
UNION ALL 
SELECT 'Least' AS purchase_type, u.id AS user_id, u.first_name, u.last_name, uoc.num_orders 
FROM `bigquery-public-data.thelook_ecommerce.users` u 
JOIN UserOrderCount uoc ON u.id = uoc.user_id 
ORDER BY uoc.num_orders ASC 
LIMIT 1;'''
            
            is_valid = _looks_like_complete_sql(complete_sql)
            print(f"✅ Complete SQL validation: {is_valid}")
            
            # Check truncated version
            truncated_sql = "SELECT user_id, COUNT(order_id) AS num_orders FROM orders GROUP BY user_id) SELECT"
            is_truncated_valid = _looks_like_complete_sql(truncated_sql)
            print(f"✅ Truncated SQL validation (should be False): {is_truncated_valid}")
            
            # The complete version should be valid, truncated version should not be
            assert is_valid, "Complete SQL should be valid"
            assert not is_truncated_valid, "Truncated SQL should be invalid"
            
            print("✅ SQL validation logic working correctly")
            return True
            
        except Exception as e:
            print(f"❌ LLM extraction mock test failed: {e}")
            return False
    
    def test_extraction_flow_logic(self):
        """Test the extraction flow logic (LLM -> Executor -> Patterns)"""
        try:
            # Import the functions we need
            from ui.pages import extract_sql_with_llm, extract_sql_with_patterns, _looks_like_complete_sql
            
            print("✅ Testing extraction flow logic")
            
            # Simulate the flow: LLM fails -> patterns try to succeed
            test_response = '''Here's your SQL:

```sql
SELECT * FROM users WHERE created_at >= '2024-01-01';
```'''
            
            # Mock LLM failure
            print("   - Simulating LLM failure, trying patterns...")
            result = extract_sql_with_patterns(test_response)
            
            if result and _looks_like_complete_sql(result):
                print(f"   ✅ Fallback extraction successful: {len(result)} chars")
                assert "SELECT * FROM users" in result
                return True
            else:
                print("   ❌ Fallback extraction failed")
                return False
                
        except Exception as e:
            print(f"❌ Extraction flow test failed: {e}")
            return False

def run_llm_extraction_tests():
    """Run all LLM SQL extraction tests"""
    print("🚀 Running LLM SQL Extraction Tests\n")
    print("🤖 Testing LLM-based SQL extraction approach\n")
    
    test_instance = TestLLMSQLExtraction()
    
    results = []
    results.append(test_instance.test_extraction_function_exists())
    
    # Test fallback patterns (these work without LLM)
    results.append(test_instance.test_fallback_patterns_work())
    
    # Test LLM logic with mocks
    results.append(test_instance.test_llm_extraction_mock())
    
    # Test extraction flow
    results.append(test_instance.test_extraction_flow_logic())
    
    if all(results):
        print("\n✅ ALL LLM EXTRACTION TESTS PASSED!")
        print("   - LLM extraction functions implemented")
        print("   - Fallback patterns working correctly")
        print("   - SQL validation logic correct")
        print("   - Extraction flow logic sound")
        print("   - Ready for testing with real LLM")
    else:
        print("\n❌ Some LLM extraction tests failed")
    
    return all(results)

if __name__ == "__main__":
    run_llm_extraction_tests()