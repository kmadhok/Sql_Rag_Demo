#!/usr/bin/env python3
"""
Test script for Google Gemini embeddings integration.

This script validates that the Gemini embeddings provider works correctly
with the embedding provider factory.
"""

import os
import sys
import logging
from pathlib import Path

# Add the utils directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.embedding_provider import get_embedding_function, get_provider_info

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_gemini_embeddings():
    """Test Gemini embeddings with various text inputs."""
    
    # Set required environment variables (use placeholders for testing)
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
        logger.warning("Using test project ID. Set GOOGLE_CLOUD_PROJECT for actual use.")
    
    # Set embedding provider to gemini
    os.environ["EMBEDDINGS_PROVIDER"] = "gemini"
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    os.environ["GEMINI_EMBEDDING_MODEL"] = "gemini-embedding-001"
    
    try:
        # Get provider info
        info = get_provider_info()
        logger.info("Provider Info:")
        for key, value in info.items():
            logger.info(f"  {key}: {value}")
        
        if info.get("error"):
            logger.error(f"Provider configuration error: {info['error']}")
            return False
        
        # Initialize embeddings
        logger.info("\nInitializing Gemini embeddings...")
        embeddings = get_embedding_function()
        
        # Test single query embedding
        test_query = "What are the top 10 customers by order count?"
        logger.info(f"Testing single query embedding: '{test_query}'")
        
        query_embedding = embeddings.embed_query(test_query)
        logger.info(f"✅ Query embedding shape: {len(query_embedding)} dimensions")
        logger.info(f"✅ First 5 values: {query_embedding[:5]}")
        
        # Test document batch embedding
        test_docs = [
            "SELECT customer_id, COUNT(*) as order_count FROM orders GROUP BY customer_id ORDER BY order_count DESC LIMIT 10",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.total > 1000",
            "CREATE TABLE customers (id INT PRIMARY KEY, name VARCHAR(255), email VARCHAR(255))"
        ]
        
        logger.info(f"\nTesting batch document embedding for {len(test_docs)} documents...")
        doc_embeddings = embeddings.embed_documents(test_docs)
        logger.info(f"✅ Document embeddings shape: {len(doc_embeddings)}x{len(doc_embeddings[0])}")
        
        # Calculate similarity between query and first document
        import numpy as np
        query_np = np.array(query_embedding)
        doc_np = np.array(doc_embeddings[0])
        
        # Cosine similarity
        similarity = np.dot(query_np, doc_np) / (np.linalg.norm(query_np) * np.linalg.norm(doc_np))
        logger.info(f"✅ Cosine similarity between query and first doc: {similarity:.4f}")
        
        logger.info("\n🎉 Gemini embeddings test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Gemini embeddings test failed: {str(e)}")
        logger.info("\nTroubleshooting tips:")
        logger.info("1. Ensure GOOGLE_CLOUD_PROJECT is set to your GCP project ID")
        logger.info("2. Ensure you're authenticated: gcloud auth application-default login")
        logger.info("3. Ensure google-genai is installed: pip install --upgrade google-genai")
        logger.info("4. Ensure your service account has 'aiplatform.user' IAM role")
        return False


def test_provider_comparison():
    """Compare information about all supported providers."""
    logger.info("\n=== Provider Comparison ===")
    
    providers = ["gemini", "openai", "ollama"]
    
    for provider in providers:
        os.environ["EMBEDDINGS_PROVIDER"] = provider
        info = get_provider_info()
        
        logger.info(f"\n{provider.upper()} Provider:")
        for key, value in info.items():
            logger.info(f"  {key}: {value}")


if __name__ == "__main__":
    logger.info("Testing Google Gemini embeddings for SQL RAG application...")
    
    # Show provider comparison
    test_provider_comparison()
    
    # Test Gemini specifically
    logger.info("\nTesting Gemini embeddings (forcing provider to 'gemini')...")
    os.environ["EMBEDDINGS_PROVIDER"] = "gemini"
    test_gemini_embeddings()