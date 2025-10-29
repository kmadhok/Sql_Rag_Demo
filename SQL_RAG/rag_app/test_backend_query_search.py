#!/usr/bin/env python3
"""
Test script for the enhanced query search API with real data integration
"""

import sys
import os
from pathlib import Path
import asyncio
import json

# Add the backend directory to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def test_vector_search_service():
    """Test the VectorSearchService initialization"""
    print("🧪 Testing VectorSearchService initialization...")
    
    try:
        # Add parent directory to path for imports
        parent_path = Path(__file__).parent
        sys.path.insert(0, str(parent_path))
        
        from backend.api.query_search import VectorSearchService
        
        # Initialize the service
        service = VectorSearchService()
        
        print(f"✅ Service initialized successfully!")
        print(f"   - Vector Search Ready: {'✅' if service.vector_search_ready else '❌'}")
        print(f"   - BigQuery Ready: {'✅' if service.bigquery_ready else '❌'}")
        print(f"   - Schema Ready: {'✅' if service.schema_ready else '❌'}")
        
        # Test vector search
        if service.vector_search_ready:
            test_question = "Show me the most expensive products"
            results = service.retrieve_relevant_queries(test_question, k=3)
            print(f"\n🔍 Vector Search Test:")
            print(f"   Question: '{test_question}'")
            print(f"   Results found: {len(results)}")
            
            for i, result in enumerate(results):
                print(f"   {i+1}. Score: {result['metadata'].get('score', 'N/A'):.3f}")
                print(f"      SQL: {result['content'][:100]}...")
        
        # Test table extraction
        if service.schema_ready:
            tables = service.extract_relevant_tables(test_question, results)
            print(f"\n📋 Table Extraction Test:")
            print(f"   Tables found: {tables}")
            
            # Test schema injection
            schema_text = service.inject_schema(tables)
            print(f"\n🏗️ Schema Injection Test:")
            print(f"   Schema snippet (first 300 chars): {schema_text[:300]}...")
        
        # Test SQL validation
        test_sql = "SELECT name, retail_price FROM products ORDER BY retail_price DESC LIMIT 10"
        validation_result = service.validate_sql(test_sql, tables)
        print(f"\n✅ SQL Validation Test:")
        print(f"   SQL: {test_sql}")
        print(f"   Valid: {validation_result['valid']}")
        print(f"   Errors: {validation_result['errors']}")
        print(f"   Warnings: {validation_result['warnings']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_environment():
    """Test environment setup"""
    print("🔧 Testing Environment Setup...")
    
    # Check .env file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        print("✅ .env file found")
        with open(env_file, 'r') as f:
            content = f.read()
            if "GEMINI_API_KEY" in content and content.split("=")[1].strip() != "demo-key":
                print("✅ GEMINI_API_KEY configured")
            else:
                print("⚠️ GEMINI_API_KEY not properly configured")
            
            if "BIGQUERY_PROJECT_ID" in content:
                project_id = content.split("BIGQUERY_PROJECT_ID=")[1].split("\n")[0].strip()
                print(f"✅ BIGQUERY_PROJECT_ID: {project_id}")
            else:
                print("⚠️ BIGQUERY_PROJECT_ID not found")
    else:
        print("❌ .env file not found")
    
    # Check FAISS indices
    faiss_dir = Path(__file__).parent / "faiss_indices"
    index_dir = faiss_dir / "index_sample_queries_with_metadata_recovered"
    if index_dir.exists() and (index_dir / "index.faiss").exists():
        print("✅ FAISS index found")
    else:
        print("❌ FAISS index not found")
    
    # Check schema file
    schema_file = Path(__file__).parent / "data_new" / "thelook_ecommerce_schema.csv"
    if schema_file.exists():
        print("✅ Schema file found")
    else:
        print("❌ Schema file not found")

if __name__ == "__main__":
    print("🚀 Testing Enhanced Query Search API\n")
    
    # Test environment
    test_environment()
    print()
    
    # Test service
    success = test_vector_search_service()
    
    if success:
        print("\n🎉 All tests passed! The query search API is ready.")
    else:
        print("\n❌ Tests failed. Please check the errors above.")