#!/usr/bin/env python3
"""
Test script for the query search API integration
"""

import requests
import json
import time

def test_search_endpoint():
    """Test the query search endpoint"""
    print("🔍 Testing query search endpoint...")
    
    url = "http://localhost:8000/api/query-search/search"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "question": "Show me the most expensive products",
        "k": 3,
        "use_gemini": True,
        "schema_injection": True,
        "sql_validation": True
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Search endpoint working!")
            print(f"   Question: {result['question']}")
            print(f"   SQL Query: {result.get('sql_query', 'N/A')}")
            print(f"   Validation Passed: {result.get('validation_passed', 'N/A')}")
            print(f"   Processing Time: {result.get('processing_time', 0):.3f}s")
            print(f"   Documents Retrieved: {result.get('usage_stats', {}).get('documents_retrieved', 0)}")
            return result
        else:
            print(f"❌ Search endpoint failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API - make sure backend is running on localhost:8000")
        return None
    except Exception as e:
        print(f"❌ Error testing search endpoint: {e}")
        return None

def test_execute_endpoint():
    """Test the SQL execution endpoint"""
    print("\n💾 Testing SQL execution endpoint...")
    
    url = "http://localhost:8000/api/query-search/execute"
    headers = {"Content-Type": "application/json"}
    
    # Use a safe test query
    payload = {
        "sql": "SELECT name, category, retail_price FROM `bigquery-public-data.thelook_ecommerce.products` ORDER BY retail_price DESC LIMIT 5",
        "dry_run": True  # Use dry run to avoid charges
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Execute endpoint working!")
            print(f"   Success: {result['success']}")
            print(f"   Rows: {result.get('row_count', 0)}")
            print(f"   Execution Time: {result.get('execution_time', 0):.3f}s")
            print(f"   Dry Run: {result['dry_run']}")
            if result.get('bytes_processed'):
                print(f"   Bytes Processed: {result['bytes_processed'] / 1024 / 1024:.2f} MB")
            return result
        else:
            print(f"❌ Execute endpoint failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API - make sure backend is running on localhost:8000")
        return None
    except Exception as e:
        print(f"❌ Error testing execute endpoint: {e}")
        return None

def test_health_endpoint():
    """Test the health check endpoint"""
    print("\n🏥 Testing health endpoint...")
    
    url = "http://localhost:8000/health"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Health endpoint working!")
            print(f"   Status: {result['status']}")
            print(f"   Service: {result['service']}")
            print(f"   Version: {result['version']}")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API - make sure backend is running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error testing health endpoint: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Query Search API Integration\n")
    
    # Test health first
    health_ok = test_health_endpoint()
    
    if health_ok:
        # Test search endpoint
        search_result = test_search_endpoint()
        
        if search_result and search_result.get('sql_query'):
            # Test execute endpoint with generated SQL
            test_execute_endpoint()
        else:
            # Test execute with default query
            test_execute_endpoint()
    else:
        print("\n❌ Health check failed - backend may not be running")
        print("Start the backend with: cd backend && python app.py")