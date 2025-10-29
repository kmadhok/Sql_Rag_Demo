#!/usr/bin/env python3
"""
Test the updated RAG service error handling
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append('..')

from dotenv import load_dotenv
load_dotenv()

def test_rag_service():
    print("🧪 Testing RAG Service Error Handling")
    print("=" * 40)
    
    try:
        from backend.services.rag_service import RAGService
        
        # Initialize service
        rag = RAGService()
        
        print(f"📊 Service Status:")
        print(f"   Real AI Available: {rag.use_real_ai}")
        print(f"   Gemini API Key Set: {'Yes' if rag.gemini_api_key else 'No'}")
        
        # Test with a question
        print("\n🔍 Testing query processing...")
        result = rag.process_query(
            question="Show me the most expensive products",
            agent_type="normal"
        )
        
        print("\n📤 Response:")
        print(f"   Has Error: {'error' in result}")
        if 'error' in result:
            print(f"   Error Code: {result.get('error_code', 'Unknown')}")
            print(f"   Message: {result.get('message', 'No message')}")
            if 'details' in result:
                print(f"   Details: {result['details']}")
        else:
            print(f"   Success: {result.get('message', 'No message')[:100]}...")
            print(f"   SQL: {result.get('sql_query', 'No SQL')}")
        
        print("\n📊 Token Usage:")
        print(f"   Prompt: {result['token_usage']['prompt']}")
        print(f"   Completion: {result['token_usage']['completion']}" )
        print(f"   Total: {result['token_usage']['total']}")
        print(f"   Processing Time: {result['processing_time']}s")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rag_service()