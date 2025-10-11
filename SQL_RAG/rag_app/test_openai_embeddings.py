#!/usr/bin/env python3
"""
Test script for OpenAI embeddings integration.

This script validates that the transition from Ollama to OpenAI embeddings works correctly.
"""

import os
import sys
from pathlib import Path

# Add the current directory to path for imports
sys.path.append(str(Path(__file__).parent))

def test_openai_embeddings():
    """Test OpenAI embeddings functionality."""
    print("🧪 Testing OpenAI Embeddings Integration")
    print("=" * 50)
    
    # Check if OpenAI API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        print("💡 Set it with: export OPENAI_API_KEY='sk-your-key-here'")
        return False
    
    print(f"✅ OpenAI API key found: {api_key[:8]}...{api_key[-4:]}")
    
    # Test the embedding provider factory
    try:
        from utils.embedding_provider import get_embedding_function
        print("✅ Successfully imported embedding provider")
    except ImportError as e:
        print(f"❌ Failed to import embedding provider: {e}")
        return False
    
    # Test creating OpenAI embedding function
    try:
        embeddings = get_embedding_function(provider="openai")
        print("✅ Successfully created OpenAI embeddings function")
        print(f"   Model: {embeddings.model}")
    except Exception as e:
        print(f"❌ Failed to create OpenAI embeddings: {e}")
        return False
    
    # Test embedding generation
    try:
        test_text = "SELECT * FROM customers WHERE age > 25"
        print(f"🔄 Testing embedding generation for: '{test_text}'")
        
        embedding_vector = embeddings.embed_query(test_text)
        print(f"✅ Successfully generated embedding")
        print(f"   Dimensions: {len(embedding_vector)}")
        print(f"   First 5 values: {embedding_vector[:5]}")
        
        # Test batch embedding
        test_texts = [
            "SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id",
            "UPDATE products SET price = price * 1.1 WHERE category = 'electronics'",
            "INSERT INTO customers (name, email) VALUES ('John Doe', 'john@example.com')"
        ]
        
        print(f"🔄 Testing batch embedding for {len(test_texts)} texts")
        batch_embeddings = embeddings.embed_documents(test_texts)
        print(f"✅ Successfully generated batch embeddings")
        print(f"   Count: {len(batch_embeddings)}")
        print(f"   Each dimension: {len(batch_embeddings[0])}")
        
    except Exception as e:
        print(f"❌ Failed to generate embeddings: {e}")
        return False
    
    # Test default provider behavior
    try:
        # Should default to OpenAI now
        default_embeddings = get_embedding_function()
        print("✅ Default provider test successful")
        print(f"   Default model: {default_embeddings.model}")
    except Exception as e:
        print(f"❌ Default provider test failed: {e}")
        return False
    
    print("\n🎉 All tests passed! OpenAI embeddings integration is working correctly.")
    print("\n📝 Next steps:")
    print("1. Clear existing FAISS indices: rm -rf faiss_indices/")
    print("2. Regenerate embeddings: python data/standalone_embedding_generator.py --csv 'sample_queries_with_metadata.csv'")
    print("3. Test the full application: streamlit run app.py")
    
    return True

def test_fallback_to_ollama():
    """Test fallback to Ollama embeddings."""
    print("\n🧪 Testing Ollama Fallback")
    print("=" * 30)
    
    try:
        from utils.embedding_provider import get_embedding_function
        ollama_embeddings = get_embedding_function(provider="ollama")
        print("✅ Ollama fallback works")
        print(f"   Model: {ollama_embeddings.model}")
    except Exception as e:
        print(f"ℹ️  Ollama fallback not available: {e}")
        print("   This is expected if Ollama is not installed")

if __name__ == "__main__":
    print("🚀 OpenAI Embeddings Integration Test")
    print("====================================\n")
    
    success = test_openai_embeddings()
    test_fallback_to_ollama()
    
    if success:
        print("\n✅ Integration test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Integration test failed!")
        sys.exit(1)