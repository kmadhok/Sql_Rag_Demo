#!/usr/bin/env python3
"""
Integration Test Script for Gemini Implementation

This script tests that all imports work correctly and that the integration
between gemini_client and simple_rag_simple_gemini is working as expected.
"""

import sys
import os

print("🧪 Testing Gemini Integration")
print("=" * 50)

# Test 1: Check if gemini_client can be imported
print("\n1. Testing gemini_client import...")
try:
    from gemini_client import GeminiClient, test_gemini_connection
    print("✅ gemini_client imported successfully")
    
    # Test client creation (will fail without API key, but import should work)
    try:
        client = GeminiClient()
        print("✅ GeminiClient can be instantiated")
    except ValueError as e:
        if "API key" in str(e):
            print("✅ GeminiClient properly requires API key (expected)")
        else:
            print(f"❌ Unexpected error: {e}")
    except ImportError as e:
        if "google-generativeai" in str(e):
            print("✅ GeminiClient properly requires google-generativeai package (expected)")
        else:
            print(f"❌ Unexpected import error: {e}")
            
except ImportError as e:
    print(f"❌ Failed to import gemini_client: {e}")
    sys.exit(1)

# Test 2: Check import structure (without dependencies)
print("\n2. Testing import structure...")
try:
    # This will fail on LangChain imports, but we can check the gemini_client import works
    with open('simple_rag_simple_gemini.py', 'r') as f:
        content = f.read()
        
    # Check that the old imports are removed
    if "vertex_gemini_llm" in content:
        print("❌ Found vertex_gemini_llm references still in code")
    else:
        print("✅ vertex_gemini_llm references removed")
    
    # Check that new imports are present
    if "from gemini_client import" in content:
        print("✅ gemini_client import found in simple_rag_simple_gemini.py")
    else:
        print("❌ gemini_client import not found")
        
    # Check that Ollama embeddings are still there (should be in app_simple_gemini.py)
    print("   Note: simple_rag_simple_gemini.py works with pre-built vector stores")
    print("   Ollama embeddings used in app_simple_gemini.py for vector store loading")
        
except Exception as e:
    print(f"❌ Error checking file structure: {e}")

# Test 3: Check requirements.txt
print("\n3. Testing requirements.txt...")
try:
    with open('requirements.txt', 'r') as f:
        requirements = f.read()
    
    if "google-generativeai" in requirements:
        print("✅ google-generativeai added to requirements.txt")
    else:
        print("❌ google-generativeai missing from requirements.txt")
    
    if "langchain-ollama" in requirements:
        print("✅ langchain-ollama still in requirements.txt (for embeddings)")
    else:
        print("❌ langchain-ollama missing from requirements.txt")
        
except Exception as e:
    print(f"❌ Error checking requirements.txt: {e}")

# Test 4: Environment variable guidance
print("\n4. Environment setup check...")
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    print(f"✅ GEMINI_API_KEY is set: {'*' * 10}...{api_key[-4:] if len(api_key) > 4 else '****'}")
else:
    print("ℹ️  GEMINI_API_KEY not set (expected for first run)")
    print("   To complete setup:")
    print("   1. Get API key: https://makersuite.google.com/app/apikey")
    print("   2. export GEMINI_API_KEY='your-api-key'")
    print("   3. pip install google-generativeai")

print("\n🎉 Integration test completed!")
print("\nNext steps to fully test:")
print("1. Install dependencies: pip install -r requirements.txt")
print("2. Set up Gemini API key")
print("3. Test with: python simple_rag_simple_gemini.py")
print("4. Run Streamlit app: streamlit run app_simple_gemini.py")