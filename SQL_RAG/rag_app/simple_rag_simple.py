#!/usr/bin/env python3
"""
Simplified RAG Implementation - Windows Compatible

A basic RAG system that works with pre-built vector stores from 
standalone_embedding_generator.py. Focused on core functionality
with Windows compatibility.

Functions:
- answer_question_simple(): Main RAG function
- test_ollama_connection(): Connection testing
"""

import time
import logging
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

# LangChain imports
from langchain_ollama import OllamaLLM
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_MODEL = "phi3"
MAX_RETRIES = 3
RETRY_DELAY = 2.0


def test_ollama_connection(model: str = OLLAMA_MODEL) -> Tuple[bool, str]:
    """
    Test connection to Ollama service
    
    Args:
        model: Ollama model name to test
        
    Returns:
        Tuple of (success, status_message)
    """
    try:
        llm = OllamaLLM(model=model)
        
        # Quick test query
        start_time = time.time()
        response = llm.invoke("Hello")
        response_time = time.time() - start_time
        
        if response and len(response.strip()) > 0:
            return True, f"Connected to {model} (response time: {response_time:.2f}s)"
        else:
            return False, f"Model {model} returned empty response"
            
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def generate_answer_with_ollama(question: str, context: str, model: str = OLLAMA_MODEL) -> Tuple[Optional[str], Dict[str, int]]:
    """
    Generate answer using Ollama LLM with retry logic
    
    Args:
        question: User question
        context: Retrieved context from vector search
        model: Ollama model name
        
    Returns:
        Tuple of (answer, token_usage_dict)
    """
    
    prompt = f"""Based on the following SQL queries and descriptions, please answer the question.

Context:
{context}

Question: {question}

Please provide a helpful answer based on the context above. If the context doesn't contain relevant information, say so clearly.

Answer:"""

    # Estimate token usage (rough approximation)
    prompt_tokens = len(prompt.split())
    
    for attempt in range(MAX_RETRIES):
        try:
            llm = OllamaLLM(model=model)
            
            start_time = time.time()
            answer = llm.invoke(prompt)
            response_time = time.time() - start_time
            
            if answer and len(answer.strip()) > 0:
                # Estimate completion tokens
                completion_tokens = len(answer.split())
                
                token_usage = {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': prompt_tokens + completion_tokens,
                    'response_time': response_time
                }
                
                logger.info(f"Generated answer in {response_time:.2f}s using {model}")
                return answer.strip(), token_usage
            else:
                logger.warning(f"Empty response from {model} on attempt {attempt + 1}")
                
        except Exception as e:
            logger.error(f"Ollama error on attempt {attempt + 1}: {e}")
            
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"Failed after {MAX_RETRIES} attempts")
    
    # Return failure case
    return None, {
        'prompt_tokens': prompt_tokens,
        'completion_tokens': 0,
        'total_tokens': prompt_tokens,
        'response_time': 0
    }


def answer_question_simple(
    question: str, 
    vector_store: FAISS, 
    k: int = 4
) -> Optional[Tuple[str, List[Document], Dict[str, int]]]:
    """
    Simple RAG function that answers questions using pre-built vector store
    
    Args:
        question: User question
        vector_store: Pre-loaded FAISS vector store
        k: Number of similar documents to retrieve
        
    Returns:
        Tuple of (answer, source_documents, token_usage) or None if failed
    """
    
    try:
        # Step 1: Retrieve relevant documents
        logger.info(f"Retrieving {k} relevant documents for: {question[:50]}...")
        
        start_time = time.time()
        relevant_docs = vector_store.similarity_search(question, k=k)
        search_time = time.time() - start_time
        
        if not relevant_docs:
            logger.warning("No relevant documents found")
            return None
        
        logger.info(f"Found {len(relevant_docs)} documents in {search_time:.2f}s")
        
        # Step 2: Prepare context from retrieved documents
        context_parts = []
        for i, doc in enumerate(relevant_docs, 1):
            # Include metadata in context for richer answers
            content = f"Document {i}:\n{doc.page_content}"
            
            # Add metadata if available
            metadata = doc.metadata
            if metadata.get('description'):
                content += f"\nDescription: {metadata['description']}"
            if metadata.get('table'):
                content += f"\nTables: {metadata['table']}"
            if metadata.get('joins'):
                content += f"\nJoins: {metadata['joins']}"
            
            context_parts.append(content)
        
        context = "\n\n" + "="*50 + "\n\n".join(context_parts)
        
        # Step 3: Generate answer using Ollama
        logger.info("Generating answer with Ollama...")
        answer, token_usage = generate_answer_with_ollama(question, context)
        
        if answer:
            logger.info("Successfully generated answer")
            return answer, relevant_docs, token_usage
        else:
            logger.error("Failed to generate answer")
            return None
            
    except Exception as e:
        logger.error(f"RAG pipeline error: {e}")
        return None


def load_and_test_vector_store(index_path: str) -> Optional[FAISS]:
    """
    Load and test a vector store (utility function)
    
    Args:
        index_path: Path to FAISS index directory
        
    Returns:
        Loaded vector store or None if failed
    """
    try:
        from langchain_ollama import OllamaEmbeddings
        
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        vector_store = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Test with a simple query
        test_docs = vector_store.similarity_search("test", k=1)
        if test_docs:
            logger.info(f"✅ Successfully loaded vector store with {len(vector_store.docstore._dict)} documents")
            return vector_store
        else:
            logger.error("Vector store loaded but returned no test results")
            return None
            
    except Exception as e:
        logger.error(f"Failed to load vector store from {index_path}: {e}")
        return None


def main():
    """
    Simple command-line interface for testing
    """
    import sys
    from pathlib import Path
    
    print("🔍 Simple RAG Test Interface")
    print("=" * 50)
    
    # Test Ollama connection
    print("Testing Ollama connection...")
    success, status = test_ollama_connection()
    
    if success:
        print(f"✅ {status}")
    else:
        print(f"❌ {status}")
        print("Make sure Ollama is running: ollama serve")
        return 1
    
    # Look for vector stores
    faiss_dir = Path(__file__).parent / "faiss_indices"
    
    if not faiss_dir.exists():
        print(f"❌ No faiss_indices directory found")
        print("Run standalone_embedding_generator.py first")
        return 1
    
    # Find available indices
    indices = [d for d in faiss_dir.iterdir() if d.is_dir() and d.name.startswith("index_")]
    
    if not indices:
        print("❌ No vector store indices found")
        print("Run standalone_embedding_generator.py first")
        return 1
    
    # Use first available index
    index_path = str(indices[0])
    print(f"Loading vector store: {indices[0].name}")
    
    vector_store = load_and_test_vector_store(index_path)
    if not vector_store:
        return 1
    
    # Interactive Q&A loop
    print("\n💬 Ask questions (type 'quit' to exit):")
    
    while True:
        try:
            question = input("\n❓ Question: ").strip()
            
            if not question or question.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            print("🔍 Searching...")
            result = answer_question_simple(question, vector_store, k=3)
            
            if result:
                answer, sources, token_usage = result
                
                print(f"\n📜 Answer:")
                print(answer)
                
                print(f"\n📊 Token Usage: {token_usage['total_tokens']:,} tokens")
                print(f"📂 Sources: {len(sources)} documents")
                
                # Show sources briefly
                for i, doc in enumerate(sources, 1):
                    source = doc.metadata.get('source', 'Unknown')
                    print(f"   {i}. {source}")
                    
            else:
                print("❌ Failed to generate answer")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())