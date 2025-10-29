#!/usr/bin/env python3
"""
Test RAG service error handling by simulating missing API key
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

print("🧪 Testing RAG Service Error Handling")
print("=" * 40)

# Remove API key temporarily to test error handling
original_key = os.environ.get('GEMINI_API_KEY')
os.environ['GEMINI_API_KEY'] = 'demo-key'  # Set to placeholder

try:
    from services.rag_service import RAGService
    
    print("\n🔍 Testing with missing/invalid API key...")
    
    # Initialize service (should fail validation)
    rag = RAGService()
    
    print(f"📊 Service Status:")
    print(f"   Real AI Available: {rag.use_real_ai}")
    print(f"   Gemini API Key Set: {'Yes' if rag.gemini_api_key else 'No'}")
    
    # Test with a question (should get error response)
    print("\n🔍 Testing query processing...")
    result = rag.process_query(
        question="Show me the most expensive products",
        agent_type="normal"
    )
    
    print("\n📤 Error Response:")
    print(f"   Has Error: {'Yes' if 'error' in result else 'No'}")
    
    if 'error' in result:
        print(f"   Error: {result['error']}")
        print(f"   Error Code: {result['error_code']}")
        print(f"   Message: {result['message']}")
        
        if 'details' in result:
            print("\n   Details:")
            for key, value in result['details'].items():
                print(f"     {key}: {value}")
        
        print(f"\n   Processing Time: {result['processing_time']}s")
        print(f"   Token Usage: {result['token_usage']}")
        print(f"   Session ID: {result['session_id']}")
        
        print("\n✅ Error handling test PASSED - Received clear error message!")
    else:
        print("❌ Error handling test FAILED - Expected error response but got success")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Restore original API key
    if original_key:
        os.environ['GEMINI_API_KEY'] = original_key
        print(f"\n🔄 Restored original API key")
    else:
        os.environ.pop('GEMINI_API_KEY', None)
        print(f"\n🔄 Removed placeholder API key")