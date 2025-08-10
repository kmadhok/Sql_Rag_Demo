#!/usr/bin/env python3
"""
Gemini-Optimized RAG Implementation - Windows Compatible

An enhanced RAG system optimized for Gemini's 1M context window that works with 
pre-built vector stores from standalone_embedding_generator.py. Features smart 
deduplication, content prioritization, and enhanced context building.

Functions:
- answer_question_simple_gemini(): Main RAG function with Gemini optimization
- test_ollama_connection(): Connection testing
- _deduplicate_chunks(): Smart Jaccard similarity deduplication  
- _prioritize_diverse_content(): Content diversification for comprehensive coverage
- _build_enhanced_context(): Intelligent context assembly for large context windows
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

# Gemini optimization constants
GEMINI_MAX_CONTEXT_TOKENS = 800000  # Stay under 1M limit with buffer
SIMILARITY_THRESHOLD = 0.7  # Jaccard similarity for deduplication


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
            return True, f"✅ {model} ready ({response_time:.2f}s response time)"
        else:
            return False, f"❌ {model} responded but returned empty response"
            
    except Exception as e:
        error_msg = str(e)
        if "Connection refused" in error_msg or "Failed to connect" in error_msg:
            return False, "❌ Ollama service not running. Start with: ollama serve"
        elif "model not found" in error_msg.lower():
            return False, f"❌ Model '{model}' not found. Install with: ollama pull {model}"
        else:
            return False, f"❌ Ollama connection error: {error_msg}"


def estimate_token_count(text: str) -> int:
    """Rough estimation of token count (4 chars ≈ 1 token)."""
    return len(text) // 4


def _deduplicate_chunks(docs: List[Document], similarity_threshold: float = SIMILARITY_THRESHOLD) -> List[Document]:
    """
    Remove highly similar chunks to avoid redundant context using Jaccard similarity.
    
    Args:
        docs: List of documents to deduplicate
        similarity_threshold: Jaccard similarity threshold (0.7 = 70% similarity)
        
    Returns:
        Filtered list of documents with duplicates removed
    """
    if len(docs) <= 1:
        return docs
    
    filtered_docs = []
    
    for doc in docs:
        is_duplicate = False
        doc_content = doc.page_content.lower()
        
        for existing_doc in filtered_docs:
            existing_content = existing_doc.page_content.lower()
            
            # Jaccard similarity check based on word sets
            doc_words = set(doc_content.split())
            existing_words = set(existing_content.split())
            
            if doc_words and existing_words:
                intersection = len(doc_words & existing_words)
                union = len(doc_words | existing_words)
                jaccard_similarity = intersection / union if union > 0 else 0
                
                if jaccard_similarity > similarity_threshold:
                    is_duplicate = True
                    logger.debug(f"Duplicate found: {jaccard_similarity:.2f} similarity")
                    break
        
        if not is_duplicate:
            filtered_docs.append(doc)
    
    logger.info(f"Deduplication: {len(docs)} -> {len(filtered_docs)} chunks ({len(docs) - len(filtered_docs)} removed)")
    return filtered_docs


def _prioritize_diverse_content(docs: List[Document], query: str) -> List[Document]:
    """
    Prioritize diverse content types for comprehensive context coverage.
    Ensures balanced representation of JOINs, aggregations, descriptions, and other patterns.
    
    Args:
        docs: List of documents to prioritize
        query: User query for context
        
    Returns:
        Reordered list with diverse content prioritized
    """
    # Group by content type indicators
    join_docs = [doc for doc in docs if 'join' in doc.page_content.lower()]
    aggregation_docs = [doc for doc in docs if any(keyword in doc.page_content.lower() 
                                                   for keyword in ['group by', 'count', 'sum', 'avg', 'having'])]
    description_docs = [doc for doc in docs if doc.metadata.get('description')]
    table_docs = [doc for doc in docs if doc.metadata.get('table')]
    other_docs = [doc for doc in docs if doc not in join_docs + aggregation_docs + description_docs]
    
    # Ensure diversity by taking from different categories
    diverse_docs = []
    categories = [
        ("JOINs", join_docs),
        ("Aggregations", aggregation_docs), 
        ("Descriptions", description_docs),
        ("Tables", table_docs),
        ("Other", other_docs)
    ]
    
    # Calculate portions for each category
    total_needed = min(len(docs), 200)  # Cap at reasonable limit
    base_portion = total_needed // len(categories)
    remainder = total_needed % len(categories)
    
    for i, (category_name, doc_list) in enumerate(categories):
        # Give extra docs to first few categories
        portion_size = base_portion + (1 if i < remainder else 0)
        selected = doc_list[:portion_size]
        diverse_docs.extend(selected)
        
        if selected:
            logger.debug(f"Selected {len(selected)} {category_name} docs")
    
    # Remove duplicates while preserving order
    seen = set()
    final_docs = []
    for doc in diverse_docs:
        doc_id = id(doc)
        if doc_id not in seen:
            seen.add(doc_id)
            final_docs.append(doc)
    
    logger.info(f"Content prioritization: {len(docs)} -> {len(final_docs)} diverse chunks")
    return final_docs


def _build_enhanced_context(docs: List[Document], query: str, max_tokens: int = GEMINI_MAX_CONTEXT_TOKENS) -> str:
    """
    Build enhanced context string optimized for large context windows.
    Includes metadata, structured formatting, and intelligent token management.
    
    Args:
        docs: List of documents to include in context
        query: User query for context
        max_tokens: Maximum tokens to use for context
        
    Returns:
        Formatted context string optimized for Gemini
    """
    if not docs:
        return "No relevant context found."
    
    context_parts = []
    current_tokens = 0
    
    # Add context header with summary
    header = f"""CONTEXT: SQL Query Analysis
User Query: "{query}"
Retrieved {len(docs)} relevant examples for comprehensive analysis.

RELEVANT SQL EXAMPLES:
"""
    context_parts.append(header)
    current_tokens += estimate_token_count(header)
    
    # Process each document with enhanced formatting
    for i, doc in enumerate(docs, 1):
        # Build document section with metadata
        doc_section = f"\n--- Example {i} ---\n"
        
        # Add description if available
        if doc.metadata.get('description'):
            doc_section += f"Description: {doc.metadata['description']}\n"
        
        # Add table information if available
        if doc.metadata.get('table'):
            doc_section += f"Tables: {doc.metadata['table']}\n"
        
        # Add join information if available
        if doc.metadata.get('joins'):
            doc_section += f"Joins: {doc.metadata['joins']}\n"
        
        # Add the SQL query
        doc_section += f"SQL:\n{doc.page_content}\n"
        
        # Check token limit
        doc_tokens = estimate_token_count(doc_section)
        if current_tokens + doc_tokens > max_tokens:
            logger.info(f"Context limit reached at {i-1}/{len(docs)} documents ({current_tokens:,} tokens)")
            break
        
        context_parts.append(doc_section)
        current_tokens += doc_tokens
    
    # Add context footer with instructions
    footer = f"""
ANALYSIS INSTRUCTIONS:
- Analyze the {len([p for p in context_parts if '--- Example' in p])} SQL examples above
- Focus on patterns, techniques, and best practices demonstrated
- Provide comprehensive answers covering multiple approaches when relevant
- Reference specific examples from the context when explaining concepts
"""
    
    # Check if footer fits
    footer_tokens = estimate_token_count(footer)
    if current_tokens + footer_tokens <= max_tokens:
        context_parts.append(footer)
        current_tokens += footer_tokens
    
    final_context = "".join(context_parts)
    logger.info(f"Enhanced context built: {current_tokens:,} tokens, {len([p for p in context_parts if '--- Example' in p])} examples")
    
    return final_context


def answer_question_simple_gemini(
    question: str, 
    vector_store: FAISS, 
    k: int = 4,
    gemini_mode: bool = False
) -> Optional[Tuple[str, List[Document], Dict[str, int]]]:
    """
    Enhanced RAG function optimized for Gemini's 1M context window
    
    Args:
        question: User question
        vector_store: Pre-loaded FAISS vector store
        k: Number of similar documents to retrieve
        gemini_mode: Enable Gemini optimizations (deduplication, large context)
        
    Returns:
        Tuple of (answer, source_documents, token_usage) or None if failed
    """
    
    try:
        # Step 1: Retrieve relevant documents
        logger.info(f"{'[GEMINI]' if gemini_mode else ''} Retrieving {k} relevant documents for: {question[:50]}...")
        
        start_time = time.time()
        docs = vector_store.similarity_search(question, k=k)
        retrieval_time = time.time() - start_time
        
        if not docs:
            logger.warning("No relevant documents found")
            return None
        
        logger.info(f"Retrieved {len(docs)} documents in {retrieval_time:.2f}s")
        
        # Step 2: Apply Gemini optimizations if enabled
        processed_docs = docs
        
        if gemini_mode:
            logger.info("Applying Gemini optimizations...")
            
            # Apply smart deduplication
            processed_docs = _deduplicate_chunks(processed_docs)
            
            # Apply content prioritization for diversity
            processed_docs = _prioritize_diverse_content(processed_docs, question)
            
            # Build enhanced context for large context windows
            context = _build_enhanced_context(processed_docs, question)
        else:
            # Build simple context for standard mode
            context = f"Question: {question}\n\nRelevant SQL examples:\n\n"
            for i, doc in enumerate(processed_docs, 1):
                context += f"Example {i}:\n{doc.page_content}\n\n"
        
        # Step 3: Generate answer using LLM
        logger.info(f"Generating answer using {OLLAMA_MODEL}...")
        
        # Build prompt
        if gemini_mode:
            prompt = f"""You are a SQL expert analyzing a comprehensive set of examples. Use the provided context to give a detailed, helpful answer.

{context}

Question: {question}

Provide a comprehensive answer that:
1. Directly addresses the user's question
2. References relevant examples from the context
3. Explains key SQL concepts and patterns
4. Suggests best practices when applicable

Answer:"""
        else:
            prompt = f"""You are a SQL expert. Based on the provided SQL examples, answer the user's question clearly and concisely.

{context}

Question: {question}

Answer:"""
        
        # Initialize LLM and generate response
        llm = OllamaLLM(model=OLLAMA_MODEL)
        
        generation_start = time.time()
        answer = llm.invoke(prompt)
        generation_time = time.time() - generation_start
        
        # Calculate token usage (rough estimates)
        prompt_tokens = estimate_token_count(prompt)
        completion_tokens = estimate_token_count(answer)
        total_tokens = prompt_tokens + completion_tokens
        
        token_usage = {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens
        }
        
        logger.info(f"Answer generated in {generation_time:.2f}s")
        logger.info(f"Token usage: {prompt_tokens:,} prompt + {completion_tokens:,} completion = {total_tokens:,} total")
        
        if gemini_mode:
            context_utilization = (prompt_tokens / 1000000) * 100
            logger.info(f"Gemini context utilization: {context_utilization:.1f}% of 1M token window")
        
        return answer.strip(), processed_docs, token_usage
        
    except Exception as e:
        logger.error(f"Error in answer_question_simple_gemini: {e}", exc_info=True)
        return None


def main():
    """Test function for the RAG system"""
    print("🔥 Testing Gemini-Optimized Simple RAG System")
    print("=" * 60)
    
    # Test Ollama connection
    print("\n1. Testing Ollama connection...")
    success, message = test_ollama_connection()
    print(message)
    
    if not success:
        print("❌ Cannot proceed without Ollama. Please start the service and try again.")
        return
    
    # Test would require a vector store to be loaded
    print("\n2. RAG system ready!")
    print("   - Smart deduplication with Jaccard similarity")
    print("   - Content prioritization for diverse examples") 
    print("   - Enhanced context building for large context windows")
    print("   - Gemini 1M context window optimization")
    print("\n✅ Use with app_simple_gemini.py for full functionality")


if __name__ == "__main__":
    main()