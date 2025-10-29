#!/usr/bin/env python3
"""
Quick API Test Script for Query Search
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8001"

def test_connection():
    """Test if backend is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running!")
            print(f"   Service: {response.json().get('service')}")
            print(f"   Version: {response.json().get('version')}")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend - make sure it's running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def test_query_search(question, k=3):
    """Test the query search API"""
    print(f"\n🔍 Testing: '{question}'")
    
    url = f"{BASE_URL}/api/query-search/search"
    payload = {
        "question": question,
        "k": k,
        "use_gemini": True,
        "schema_injection": True,
        "sql_validation": True
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! ({end_time - start_time:.2f}s)")
            
            # Extract key information
            sql_query = result.get('sql_query', 'N/A')
            validation_passed = result.get('validation_passed', 'N/A')
            processing_time = result.get('processing_time', 0)
            documents_retrieved = result.get('usage_stats', {}).get('documents_retrieved', 0)
            
            print(f"   📝 SQL: {sql_query}")
            print(f"   ✅ Validation: {validation_passed}")
            print(f"   ⏱️  Time: {processing_time:.3f}s")
            print(f"   📚 Docs: {documents_retrieved}")
            
            if result.get('validation_errors'):
                print(f"   ⚠️  Errors: {', '.join(result['validation_errors'])}")
            
            return sql_query, validation_passed
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None, None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

def test_sql_execution(sql_query, dry_run=True):
    """Test SQL execution"""
    if not sql_query or sql_query == 'N/A':
        print("\n⚠️  No SQL query to execute")
        return
        
    print(f"\n💾 Testing SQL execution (dry_run={'YES' if dry_run else 'NO'}):")
    print(f"   SQL: {sql_query}")
    
    url = f"{BASE_URL}/api/query-search/execute"
    payload = {
        "sql": sql_query,
        "dry_run": dry_run
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Execution successful!")
                print(f"   📊 Rows: {result.get('row_count', 0)}")
                print(f"   ⏱️  Time: {result.get('execution_time', 0):.3f}s")
                if result.get('bytes_processed'):
                    print(f"   💾 Bytes: {result['bytes_processed'] / 1024 / 1024:.2f} MB")
                print(f"   🗄️  Cache hit: {result.get('cache_hit', 'N/A')}")
            else:
                print(f"❌ Execution failed: {result.get('error_message', 'Unknown error')}")
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main test function"""
    print("🚀 Query Search API Quick Test")
    print("=" * 40)
    
    # Test connection
    if not test_connection():
        print("\n❌ Please start the backend first:")
        print("   cd backend && python app.py")
        sys.exit(1)
    
    # Test questions
    test_questions = [
        "Show me the most expensive products",
        "Count users by gender", 
        "Find customers with the most orders",
        "What is the average order value?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n📝 Test {i}/{len(test_questions)}")
        print("-" * 30)
        
        sql_query, validation_passed = test_query_search(question)
        
        # Test execution if SQL was generated and validated
        if sql_query and validation_passed and i <= 2:  # Only test execution for first 2
            test_sql_execution(sql_query, dry_run=True)
        
        if i < len(test_questions):
            time.sleep(1)  # Brief pause between tests
    
    print("\n🎉 Testing complete!")
    print("\n💡 Tips:")
    print("   - Use dry_run=True for SQL execution to avoid costs")
    print("   - Check backend logs for detailed information")
    print("   - For full API docs, visit: http://localhost:8000/docs")
    print("   - For comprehensive cURL examples, see: API_CURL_GUIDE.md")

if __name__ == "__main__":
    main()