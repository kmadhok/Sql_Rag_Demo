#!/usr/bin/env python3
"""
Direct test of RAG service from backend context
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
env_path = backend_dir.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
    print(f"✅ Loaded environment from: {env_path}")

print("🧪 Testing RAG Service from Backend Context")
print("=" * 45)

try:
    from services.rag_service import RAGService
    
    # Initialize service
    rag = RAGService()
    
    print(f"📊 Service Status:")
    print(f"   Real AI Available: {rag.use_real_ai}")
    print(f"   Gemini API Key Set: {'Yes' if rag.gemini_api_key else 'No'}")
    if rag.gemini_api_key:
        print(f"   API Key Length: {len(rag.gemini_api_key)} chars")
        print(f"   API Key Preview: {rag.gemini_api_key[:10]}...")
    
    # Test with a question
    print("\n🔍 Testing query processing...")
    test_questions = [
        "Show me the most expensive products",
        "How many users are there?",
        "Find customers with the most orders"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n   Test {i}: {question}")
        result = rag.process_query(
            question=question,
            agent_type="normal"
        )
        
        print(f"   Result Type: {'Error' if 'error' in result else 'Success'}")
        if 'error' in result:
            print(f"   Error Code: {result.get('error_code', 'Unknown')}")
            print(f"   Message: {result.get('message', 'No message')}")
            
            # Show helpful details if available
            if 'details' in result and 'solution' in result['details']:
                print(f"   Solution: {result['details']['solution']}")
        else:
            print(f"   Success: {result.get('message', 'No message')[:80]}...")
            print(f"   SQL: {result.get('sql_query', 'No SQL')}")
        
        print(f"   Processing Time: {result['processing_time']}s")
        print(f"   Tokens: {result['token_usage']['total']}")
    
    print("\n✅ RAG Service test completed")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()