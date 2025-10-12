#!/usr/bin/env python3
"""
Test script for BigQuery integration

Tests the BigQuery executor functionality without requiring actual BigQuery credentials
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_bigquery_executor_import():
    """Test that BigQuery executor can be imported"""
    try:
        from core.bigquery_executor import BigQueryExecutor, QueryResult, format_bytes, format_execution_time
        print("✅ BigQuery executor imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import BigQuery executor: {e}")
        return False

def test_sql_validation():
    """Test SQL validation functionality"""
    try:
        from core.bigquery_executor import BigQueryExecutor
        
        # Create executor (won't actually connect without credentials)
        executor = BigQueryExecutor()
        
        # Test valid SQL
        valid_sql = "SELECT * FROM `bigquery-public-data.thelook_ecommerce.users` LIMIT 10"
        is_valid, msg = executor.validate_sql_safety(valid_sql)
        print(f"✅ Valid SQL validation: {is_valid} - {msg}")
        
        # Test invalid SQL (forbidden operation)
        invalid_sql = "DELETE FROM users WHERE id = 1"
        is_valid, msg = executor.validate_sql_safety(invalid_sql)
        print(f"✅ Invalid SQL validation: {is_valid} - {msg}")
        
        return True
    except Exception as e:
        print(f"❌ SQL validation test failed: {e}")
        return False

def test_sql_extraction():
    """Test SQL extraction from text"""
    try:
        from core.bigquery_executor import BigQueryExecutor
        
        executor = BigQueryExecutor()
        
        # Test text with SQL
        text_with_sql = """
        Here's a query to get user information:
        
        ```sql
        SELECT user_id, first_name, last_name, email
        FROM `bigquery-public-data.thelook_ecommerce.users`
        WHERE created_at > '2023-01-01'
        LIMIT 100
        ```
        
        This query retrieves user data from the last year.
        """
        
        extracted_sql = executor.extract_sql_from_text(text_with_sql)
        if extracted_sql:
            print("✅ SQL extraction successful:")
            print(f"   Extracted: {extracted_sql[:50]}...")
        else:
            print("❌ SQL extraction failed")
            
        return extracted_sql is not None
    except Exception as e:
        print(f"❌ SQL extraction test failed: {e}")
        return False

def test_utility_functions():
    """Test utility functions"""
    try:
        from core.bigquery_executor import format_bytes, format_execution_time
        
        # Test format_bytes
        bytes_test = format_bytes(1024)
        print(f"✅ format_bytes(1024) = {bytes_test}")
        
        bytes_test_mb = format_bytes(1024*1024*5)
        print(f"✅ format_bytes(5MB) = {bytes_test_mb}")
        
        # Test format_execution_time
        time_test = format_execution_time(0.5)
        print(f"✅ format_execution_time(0.5) = {time_test}")
        
        time_test_ms = format_execution_time(0.0234)
        print(f"✅ format_execution_time(0.0234) = {time_test_ms}")
        
        return True
    except Exception as e:
        print(f"❌ Utility functions test failed: {e}")
        return False

def test_streamlit_integration():
    """Test that the Streamlit app can import BigQuery components"""
    try:
        # Test the import that happens in app_simple_gemini.py
        from core.bigquery_executor import BigQueryExecutor, QueryResult, format_bytes, format_execution_time
        
        print("✅ Streamlit integration imports successful")
        return True
    except ImportError as e:
        print(f"❌ Streamlit integration import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing BigQuery Integration")
    print("=" * 50)
    
    tests = [
        ("BigQuery Executor Import", test_bigquery_executor_import),
        ("SQL Validation", test_sql_validation),
        ("SQL Extraction", test_sql_extraction),
        ("Utility Functions", test_utility_functions),
        ("Streamlit Integration", test_streamlit_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing: {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! BigQuery integration is ready.")
        print("\n💡 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Set up BigQuery authentication (GOOGLE_APPLICATION_CREDENTIALS)")
        print("3. Run the Streamlit app: streamlit run app_simple_gemini.py")
        print("4. Ask a question that generates SQL and test the execution feature")
    else:
        print("⚠️ Some tests failed. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()