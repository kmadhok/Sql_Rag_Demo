#!/usr/bin/env python3
"""
Test Script for Conversation Persistence System

Tests the complete conversation persistence workflow including:
- Firestore client initialization
- ConversationManager operations (save, load, list, delete)
- Error handling and fallback mechanisms
- Integration with Streamlit session state simulation

Run this script to validate the conversation persistence system before deployment.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Any
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_firestore_client():
    """Test Firestore client initialization and connection."""
    print("🧪 Testing Firestore Client...")
    
    try:
        from utils.firestore_client import get_firestore_client, is_firestore_available
        
        # Test environment check
        env_available = is_firestore_available()
        print(f"   Environment check: {'✅' if env_available else '❌'}")
        
        # Test client initialization
        client = get_firestore_client()
        client_available = client.is_available
        print(f"   Client available: {'✅' if client_available else '❌'}")
        
        # Test connection
        status = client.test_connection()
        print(f"   Connection test: {'✅' if status['available'] else '❌'}")
        
        if status.get('error'):
            print(f"   Error: {status['error']}")
        
        if status.get('project_id'):
            print(f"   Project ID: {status['project_id']}")
        
        return client_available
        
    except Exception as e:
        print(f"   ❌ Firestore client test failed: {e}")
        return False

def test_conversation_manager():
    """Test ConversationManager basic operations."""
    print("\n🧪 Testing ConversationManager...")
    
    try:
        from core.conversation_manager import get_conversation_manager
        
        # Initialize manager
        manager = get_conversation_manager()
        
        # Test storage status
        status = manager.get_storage_status()
        print(f"   Storage mode: {status['storage_mode']}")
        print(f"   Firestore available: {'✅' if status['firestore_available'] else '❌'}")
        
        # Test user session
        test_user_session = f"test_user_{int(time.time())}"
        
        # Test conversation data
        test_messages = [
            {
                'role': 'user',
                'content': 'How do I optimize SQL queries for better performance?',
                'agent_type': None
            },
            {
                'role': 'assistant',
                'content': 'Here are some SQL optimization techniques: 1) Use proper indexing, 2) Avoid SELECT *, 3) Use WHERE clauses effectively...',
                'agent_type': None,
                'sources': [],
                'token_usage': {'total_tokens': 150, 'prompt_tokens': 50, 'completion_tokens': 100}
            },
            {
                'role': 'user',
                'content': '@explain what are indexes and how do they work?',
                'agent_type': 'explain'
            },
            {
                'role': 'assistant',
                'content': 'Indexes are database objects that improve query performance by creating a sorted reference to table data...',
                'agent_type': 'explain',
                'sources': [],
                'token_usage': {'total_tokens': 200, 'prompt_tokens': 60, 'completion_tokens': 140}
            }
        ]
        
        # Test save conversation
        print("   Testing save conversation...")
        conv_id, save_success = manager.save_conversation(
            messages=test_messages,
            user_session_id=test_user_session
        )
        print(f"   Save result: {'✅' if save_success else '❌'} (ID: {conv_id})")
        
        if not save_success:
            print("   ⚠️ Save failed, testing will continue with fallback storage")
        
        # Test load conversation
        print("   Testing load conversation...")
        loaded_conv = manager.load_conversation(conv_id, test_user_session)
        load_success = loaded_conv is not None
        print(f"   Load result: {'✅' if load_success else '❌'}")
        
        if load_success:
            print(f"   Loaded {len(loaded_conv.get('messages', []))} messages")
            print(f"   Title: {loaded_conv.get('title', 'N/A')}")
            print(f"   Tags: {', '.join(loaded_conv.get('tags', []))}")
        
        # Test list conversations
        print("   Testing list conversations...")
        conversations = manager.list_conversations(test_user_session, limit=10)
        print(f"   Found {len(conversations)} conversation(s)")
        
        for conv in conversations:
            print(f"     - {conv.title} ({conv.message_count} messages)")
        
        # Test search conversations
        print("   Testing search conversations...")
        search_results = manager.list_conversations(
            test_user_session, 
            limit=10, 
            search_term="sql"
        )
        print(f"   Search results: {len(search_results)} conversation(s)")
        
        # Test delete conversation
        print("   Testing delete conversation...")
        delete_success = manager.delete_conversation(conv_id, test_user_session)
        print(f"   Delete result: {'✅' if delete_success else '❌'}")
        
        # Verify deletion
        verify_conv = manager.load_conversation(conv_id, test_user_session)
        deletion_verified = verify_conv is None
        print(f"   Deletion verified: {'✅' if deletion_verified else '❌'}")
        
        return save_success and load_success and delete_success
        
    except Exception as e:
        print(f"   ❌ ConversationManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_streamlit_integration():
    """Test Streamlit integration functions."""
    print("\n🧪 Testing Streamlit Integration...")
    
    try:
        # Mock Streamlit session state
        class MockSessionState:
            def __init__(self):
                self.data = {}
            
            def get(self, key, default=None):
                return self.data.get(key, default)
            
            def __getitem__(self, key):
                return self.data[key]
            
            def __setitem__(self, key, value):
                self.data[key] = value
            
            def __contains__(self, key):
                return key in self.data
        
        # Mock streamlit module
        class MockStreamlit:
            def __init__(self):
                self.session_state = MockSessionState()
        
        # Temporarily replace streamlit import
        sys.modules['streamlit'] = MockStreamlit()
        
        # Test user session ID generation
        from app_simple_gemini import get_user_session_id, auto_save_conversation
        
        user_session_1 = get_user_session_id()
        user_session_2 = get_user_session_id()
        
        print(f"   User session ID generation: {'✅' if user_session_1 == user_session_2 else '❌'}")
        print(f"   Generated ID: {user_session_1}")
        
        # Test auto-save function
        print("   Testing auto-save function...")
        
        # Set up mock conversation
        st = sys.modules['streamlit']
        st.session_state.chat_messages = [
            {'role': 'user', 'content': 'Test message', 'agent_type': None}
        ]
        st.session_state.conversation_manager = get_conversation_manager()
        
        # Test auto-save
        auto_save_conversation()
        print("   Auto-save function: ✅ (no errors)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Streamlit integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up mock
        if 'streamlit' in sys.modules:
            del sys.modules['streamlit']

def test_error_handling():
    """Test error handling and fallback mechanisms."""
    print("\n🧪 Testing Error Handling...")
    
    try:
        from core.conversation_manager import ConversationManager
        
        # Test with invalid user session
        manager = ConversationManager()
        
        # Test load non-existent conversation
        print("   Testing load non-existent conversation...")
        result = manager.load_conversation("invalid_id", "invalid_session")
        not_found_success = result is None
        print(f"   Non-existent load: {'✅' if not_found_success else '❌'}")
        
        # Test delete non-existent conversation
        print("   Testing delete non-existent conversation...")
        delete_result = manager.delete_conversation("invalid_id", "invalid_session")
        delete_invalid_success = not delete_result  # Should return False
        print(f"   Non-existent delete: {'✅' if delete_invalid_success else '❌'}")
        
        # Test list with empty results
        print("   Testing list with empty session...")
        empty_list = manager.list_conversations("empty_session")
        empty_list_success = len(empty_list) == 0
        print(f"   Empty list: {'✅' if empty_list_success else '❌'}")
        
        # Test save with empty messages
        print("   Testing save with empty messages...")
        empty_id, empty_save = manager.save_conversation([], "test_session")
        empty_save_handled = isinstance(empty_id, str)  # Should still create ID
        print(f"   Empty save handling: {'✅' if empty_save_handled else '❌'}")
        
        return (not_found_success and delete_invalid_success and 
                empty_list_success and empty_save_handled)
        
    except Exception as e:
        print(f"   ❌ Error handling test failed: {e}")
        return False

def run_comprehensive_test():
    """Run comprehensive test of the conversation persistence system."""
    print("🚀 Conversation Persistence System - Comprehensive Test")
    print("=" * 60)
    
    test_results = []
    
    # Run all tests
    test_results.append(("Firestore Client", test_firestore_client()))
    test_results.append(("ConversationManager", test_conversation_manager()))
    test_results.append(("Streamlit Integration", test_streamlit_integration()))
    test_results.append(("Error Handling", test_error_handling()))
    
    # Print results summary
    print("\n📊 Test Results Summary")
    print("-" * 30)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<25} {status}")
        if result:
            passed += 1
    
    total = len(test_results)
    success_rate = (passed / total) * 100
    
    print(f"\nOverall: {passed}/{total} tests passed ({success_rate:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Conversation persistence system is ready.")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Check configuration and dependencies.")
        return False

def check_environment():
    """Check environment setup and provide guidance."""
    print("\n🔧 Environment Check")
    print("-" * 20)
    
    # Check Google Cloud credentials
    gcp_project = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT')
    gcp_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    print(f"GCP Project: {gcp_project or 'Not set'}")
    print(f"GCP Credentials: {'Set' if gcp_credentials else 'Not set'}")
    
    if not gcp_project and not gcp_credentials:
        print("\n💡 Setup Recommendations:")
        print("   For local testing:")
        print("   1. Install Google Cloud CLI: https://cloud.google.com/sdk/docs/install")
        print("   2. Run: gcloud auth application-default login")
        print("   3. Set project: gcloud config set project YOUR_PROJECT_ID")
        print("\n   For Cloud Run (automatic):")
        print("   1. Service account authentication is handled automatically")
        print("   2. Ensure Firestore API is enabled")
        print("   3. Ensure service account has datastore.user role")

if __name__ == "__main__":
    print("SQL RAG Application - Conversation Persistence Test")
    print("=" * 55)
    
    # Check environment first
    check_environment()
    
    # Run comprehensive tests
    success = run_comprehensive_test()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)