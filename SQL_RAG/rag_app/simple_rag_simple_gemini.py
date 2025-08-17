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
import os
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

# LangChain imports
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Gemini imports
from gemini_client import GeminiClient, test_gemini_connection

# Import hybrid search functionality
try:
    from hybrid_retriever import HybridRetriever, SearchWeights, HybridSearchResult
    HYBRID_SEARCH_AVAILABLE = True
except ImportError:
    logger.warning("Hybrid search not available - install rank-bm25: pip install rank-bm25")
    HYBRID_SEARCH_AVAILABLE = False

# Import query rewriting functionality
try:
    from query_rewriter import QueryRewriter, create_query_rewriter
    QUERY_REWRITING_AVAILABLE = True
except ImportError:
    logger.warning("Query rewriting not available - check query_rewriter.py")
    QUERY_REWRITING_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GEMINI_MODEL = "gemini-2.5-flash-lite"
MAX_RETRIES = 3
RETRY_DELAY = 2.0

# Gemini optimization constants
GEMINI_MAX_CONTEXT_TOKENS = 800000  # Stay under 1M limit with buffer
SIMILARITY_THRESHOLD = 0.7  # Jaccard similarity for deduplication


def test_gemini_connection_simple(model: str = GEMINI_MODEL) -> Tuple[bool, str]:
    """
    Test connection to Gemini service
    
    Args:
        model: Gemini model name to test
        
    Returns:
        Tuple of (success, status_message)
    """
    return test_gemini_connection(model=model)


def estimate_token_count(text: str) -> int:
    """Rough estimation of token count (4 chars ≈ 1 token)."""
    return len(text) // 4


def _extract_documents_from_vector_store(vector_store: FAISS) -> List[Document]:
    """
    Extract all documents from a FAISS vector store for hybrid retriever initialization
    
    Args:
        vector_store: FAISS vector store
        
    Returns:
        List of Document objects
    """
    try:
        # Access the docstore to get all documents
        documents = []
        docstore = vector_store.docstore
        
        if hasattr(docstore, '_dict'):
            # Standard FAISS docstore
            for doc_id, doc in docstore._dict.items():
                if isinstance(doc, Document):
                    documents.append(doc)
        else:
            logger.warning("Unable to extract documents from vector store - using vector search only")
            return []
        
        logger.info(f"Extracted {len(documents)} documents from vector store for hybrid search")
        return documents
        
    except Exception as e:
        logger.error(f"Failed to extract documents from vector store: {e}")
        return []


def _initialize_hybrid_retriever(vector_store: FAISS) -> Optional[HybridRetriever]:
    """
    Initialize hybrid retriever with vector store and documents
    
    Args:
        vector_store: FAISS vector store
        
    Returns:
        HybridRetriever instance or None if initialization fails
    """
    if not HYBRID_SEARCH_AVAILABLE:
        return None
    
    try:
        # Extract documents from vector store
        documents = _extract_documents_from_vector_store(vector_store)
        
        if not documents:
            logger.warning("No documents extracted - falling back to vector search only")
            return None
        
        # Initialize hybrid retriever
        hybrid_retriever = HybridRetriever(vector_store, documents)
        logger.info("✅ Hybrid retriever initialized successfully")
        return hybrid_retriever
        
    except Exception as e:
        logger.error(f"Failed to initialize hybrid retriever: {e}")
        return None


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


def get_agent_prompt_template(agent_type: Optional[str], question: str, schema_section: str, conversation_section: str, context: str, gemini_mode: bool = False) -> str:
    """
    Get specialized prompt template based on agent type
    
    Args:
        agent_type: Agent specialization type ("explain", "create", or None)
        question: User question
        schema_section: Database schema information
        conversation_section: Previous conversation context
        context: Retrieved SQL examples context
        gemini_mode: Whether using Gemini optimizations
        
    Returns:
        Formatted prompt string for the specific agent
    """
    
    if agent_type == "explain":
        # Explanation Agent - Focus on detailed breakdowns and educational content
        if gemini_mode:
            return f"""You are a SQL Explanation Expert. Your role is to provide detailed, educational explanations of SQL queries, concepts, and database operations. Use the provided schema, context, and conversation history to give comprehensive explanations.
{schema_section}
{conversation_section}
{context}

Current Question: {question}

As an Explanation Expert, provide a comprehensive answer that:
1. Breaks down complex SQL concepts into understandable parts
2. Explains step-by-step how queries work and why they're structured that way
3. References relevant examples from the context to illustrate points
4. Uses the database schema to explain table relationships and data flow
5. Builds on previous conversation when relevant
6. Explains the "why" behind SQL patterns and best practices
7. Uses clear, educational language suitable for learning

Focus on education and understanding rather than just providing answers.

Explanation:"""
        else:
            return f"""You are a SQL Explanation Expert. Provide detailed explanations of SQL queries and concepts using the provided schema, examples, and conversation history.
{schema_section}
{conversation_section}
{context}

Current Question: {question}

Explain clearly and educationally, breaking down concepts step-by-step.

Explanation:"""
    
    elif agent_type == "create":
        # Creation Agent - Focus on generating working SQL code
        if gemini_mode:
            return f"""You are a SQL Creation Expert. Your role is to generate efficient, working SQL queries from natural language requirements. Use the provided schema, context, and conversation history to create optimal SQL solutions.
{schema_section}
{conversation_section}
{context}

Current Requirement: {question}

As a Creation Expert, provide a comprehensive solution that:
1. Generates working SQL code that meets the specified requirements
2. Uses appropriate table structures and relationships from the schema
3. Follows SQL best practices and performance considerations
4. References similar patterns from the context examples when applicable
5. Builds on previous conversation context when relevant
6. Includes clear comments explaining the approach
7. Considers edge cases and data integrity
8. Suggests optimizations or alternative approaches when beneficial

Focus on creating practical, efficient SQL solutions.

SQL Solution:"""
        else:
            return f"""You are a SQL Creation Expert. Generate efficient SQL queries from requirements using the provided schema, examples, and conversation history.
{schema_section}
{conversation_section}
{context}

Current Requirement: {question}

Create working SQL code that meets the requirements with clear comments.

SQL Solution:"""
    
    else:
        # Default behavior - General SQL assistance
        if gemini_mode:
            return f"""You are a SQL expert analyzing a comprehensive set of examples. Use the provided schema, context, and conversation history to give a detailed, helpful answer.
{schema_section}
{conversation_section}
{context}

Current Question: {question}

Provide a comprehensive answer that:
1. Directly addresses the user's current question
2. References relevant examples from the context
3. Uses the database schema when explaining table structures and relationships
4. Builds on previous conversation when relevant
5. Explains key SQL concepts and patterns
6. Suggests best practices when applicable

Answer:"""
        else:
            return f"""You are a SQL expert. Based on the provided database schema, SQL examples, and conversation history, answer the user's question clearly and concisely.
{schema_section}
{conversation_section}
{context}

Current Question: {question}

Answer:"""


def answer_question_simple_gemini(
    question: str, 
    vector_store: FAISS, 
    k: int = 4,
    gemini_mode: bool = False,
    hybrid_search: bool = False,
    search_weights: Optional[SearchWeights] = None,
    auto_adjust_weights: bool = True,
    query_rewriting: bool = False,
    schema_manager=None,
    conversation_context: str = "",
    agent_type: Optional[str] = None
) -> Optional[Tuple[str, List[Document], Dict[str, Any]]]:
    """
    Enhanced RAG function optimized for Gemini's 1M context window with hybrid search and query rewriting support
    
    Args:
        question: User question
        vector_store: Pre-loaded FAISS vector store
        k: Number of similar documents to retrieve
        gemini_mode: Enable Gemini optimizations (deduplication, large context)
        hybrid_search: Enable hybrid search (vector + keyword BM25)
        search_weights: Custom search weights (vector_weight, keyword_weight)
        auto_adjust_weights: Automatically adjust weights based on query analysis
        query_rewriting: Enable intelligent query rewriting for better retrieval
        schema_manager: Optional SchemaManager for smart schema injection (reduces noise from 39K+ to ~100-500 relevant rows)
        conversation_context: Previous conversation history for context continuity
        agent_type: Agent specialization type ("explain", "create", or None for default)
        
    Returns:
        Tuple of (answer, source_documents, enhanced_token_usage) or None if failed
    """
    
    try:
        # Step 0: Query rewriting for enhanced retrieval (optional)
        rewrite_data = None
        search_query = question  # Default to original question
        
        if query_rewriting and QUERY_REWRITING_AVAILABLE:
            # Initialize query rewriter (cached for performance)
            if not hasattr(answer_question_simple_gemini, '_query_rewriter'):
                # Use Gemini for query rewriting, get project from environment
                project = os.getenv('GOOGLE_CLOUD_PROJECT')
                answer_question_simple_gemini._query_rewriter = create_query_rewriter(
                    project=project,
                    auto_select_model=True  # Enable intelligent model selection
                )
            
            query_rewriter = answer_question_simple_gemini._query_rewriter
            
            try:
                logger.info(f"Rewriting query for enhanced retrieval: {question[:50]}...")
                rewrite_data = query_rewriter.rewrite_query(question, auto_select_model=True)
                
                if rewrite_data['confidence'] >= 0.6:  # Use rewritten query if confidence is high
                    search_query = rewrite_data['rewritten_query']
                    logger.info(f"Using rewritten query (confidence: {rewrite_data['confidence']:.2f}): {search_query[:50]}...")
                else:
                    logger.info(f"Low confidence rewrite ({rewrite_data['confidence']:.2f}), using original query")
                    search_query = question
                    
            except Exception as e:
                logger.warning(f"Query rewriting failed, using original query: {e}")
                search_query = question
        
        # Step 1: Retrieve relevant documents with hybrid search support
        search_method = "hybrid" if hybrid_search and HYBRID_SEARCH_AVAILABLE else "vector"
        query_info = f"original: '{question[:30]}...'" if search_query != question else f"'{question[:50]}...'"
        logger.info(f"{'[GEMINI]' if gemini_mode else ''} Retrieving {k} relevant documents using {search_method} search for: {query_info}")
        
        start_time = time.time()
        hybrid_results = []
        
        if hybrid_search and HYBRID_SEARCH_AVAILABLE:
            # Initialize hybrid retriever (cached for performance)
            if not hasattr(answer_question_simple_gemini, '_hybrid_retriever'):
                answer_question_simple_gemini._hybrid_retriever = _initialize_hybrid_retriever(vector_store)
            
            hybrid_retriever = answer_question_simple_gemini._hybrid_retriever
            
            if hybrid_retriever:
                # Perform hybrid search
                hybrid_results = hybrid_retriever.hybrid_search(
                    search_query, 
                    k=k, 
                    weights=search_weights,
                    auto_adjust_weights=auto_adjust_weights
                )
                docs = [result.document for result in hybrid_results]
                logger.info(f"Hybrid search: {len(docs)} documents retrieved")
            else:
                # Fallback to vector search
                docs = vector_store.similarity_search(search_query, k=k)
                logger.warning("Hybrid search failed, using vector search fallback")
        else:
            # Standard vector search
            docs = vector_store.similarity_search(search_query, k=k)
            logger.info(f"Vector search: {len(docs)} documents retrieved")
        
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
        
        # Step 2.5: Smart schema filtering (extract relevant tables and inject schema)
        relevant_schema = ""
        if schema_manager:
            try:
                # Extract table names from retrieved documents
                relevant_tables = schema_manager.extract_tables_from_documents(processed_docs)
                
                # Also extract tables from the user question
                question_tables = schema_manager.extract_tables_from_content(question)
                relevant_tables.extend(question_tables)
                
                if relevant_tables:
                    # Filter schema to only relevant tables (39K → ~100-500 rows)
                    relevant_schema = schema_manager.get_relevant_schema(relevant_tables)
                    
                    if relevant_schema:
                        logger.info(f"Smart schema filtering: {len(relevant_tables)} tables identified, schema filtered for injection")
                    else:
                        logger.info("No matching schema found for identified tables")
                else:
                    logger.info("No tables identified from retrieved documents")
                    
            except Exception as e:
                logger.warning(f"Schema filtering failed, continuing without schema: {e}")
                relevant_schema = ""
        
        if gemini_mode:
            # Build enhanced context for large context windows
            context = _build_enhanced_context(processed_docs, question)
        else:
            # Build simple context for standard mode
            context = f"Question: {question}\n\nRelevant SQL examples:\n\n"
            for i, doc in enumerate(processed_docs, 1):
                context += f"Example {i}:\n{doc.page_content}\n\n"
        
        # Step 3: Generate answer using LLM
        logger.info(f"Generating answer using {GEMINI_MODEL}...")
        
        # Build prompt with agent specialization, schema injection, and conversation context
        schema_section = f"\n{relevant_schema}\n" if relevant_schema else ""
        conversation_section = f"\nPrevious conversation:\n{conversation_context}\n" if conversation_context.strip() else ""
        
        # Use agent-specific prompt template
        prompt = get_agent_prompt_template(
            agent_type=agent_type,
            question=question,
            schema_section=schema_section,
            conversation_section=conversation_section,
            context=context,
            gemini_mode=gemini_mode
        )
        
        # Initialize LLM and generate response
        llm = GeminiClient(model=GEMINI_MODEL)
        
        generation_start = time.time()
        answer = llm.invoke(prompt)
        generation_time = time.time() - generation_start
        
        # Calculate token usage (rough estimates) with enhanced information
        prompt_tokens = estimate_token_count(prompt)
        completion_tokens = estimate_token_count(answer)
        total_tokens = prompt_tokens + completion_tokens
        
        # Enhanced token usage with search method, agent type, and query rewriting information
        token_usage = {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'search_method': search_method,
            'retrieval_time': retrieval_time,
            'documents_retrieved': len(docs),
            'documents_processed': len(processed_docs),
            'agent_type': agent_type
        }
        
        # Add query rewriting information if available
        if rewrite_data:
            token_usage.update({
                'query_rewriting': {
                    'enabled': True,
                    'rewritten_query': rewrite_data['rewritten_query'],
                    'confidence': rewrite_data['confidence'],
                    'rewrite_method': rewrite_data['rewrite_method'],
                    'rewrite_time': rewrite_data['rewrite_time'],
                    'query_used': search_query,
                    'query_changed': search_query != question
                }
            })
        else:
            token_usage['query_rewriting'] = {'enabled': False}
        
        # Add schema filtering information if available
        if schema_manager:
            schema_tokens = estimate_token_count(relevant_schema) if relevant_schema else 0
            token_usage.update({
                'schema_filtering': {
                    'enabled': True,
                    'relevant_tables': len(relevant_tables) if 'relevant_tables' in locals() else 0,
                    'schema_tokens': schema_tokens,
                    'schema_available': bool(relevant_schema),
                    'total_schema_tables': schema_manager.table_count,
                    'schema_coverage': f"{len(relevant_tables) if 'relevant_tables' in locals() else 0}/{schema_manager.table_count}" if 'relevant_tables' in locals() else "0/0"
                }
            })
        else:
            token_usage['schema_filtering'] = {'enabled': False}
        
        # Add hybrid search specific information
        if hybrid_results:
            search_breakdown = {}
            for result in hybrid_results:
                method = result.search_method
                search_breakdown[method] = search_breakdown.get(method, 0) + 1
            
            token_usage.update({
                'hybrid_search_breakdown': search_breakdown,
                'fusion_scores_available': True,
                'search_weights': {
                    'vector_weight': search_weights.vector_weight if search_weights else 0.7,
                    'keyword_weight': search_weights.keyword_weight if search_weights else 0.3
                } if search_weights else None
            })
        
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
    
    # Test Gemini connection
    print("\n1. Testing Gemini connection...")
    success, message = test_gemini_connection_simple()
    print(message)
    
    if not success:
        print("❌ Cannot proceed without Gemini. Please check your setup.")
        print("\n🔧 Setup steps:")
        print("1. Install: pip install google-generativeai")
        print("2. Get API key: https://makersuite.google.com/app/apikey")
        print("3. Set environment variable: export GEMINI_API_KEY='your-api-key'")
        return
    
    # Test would require a vector store to be loaded
    print("\n2. RAG system ready!")
    print("   - Smart deduplication with Jaccard similarity")
    print("   - Content prioritization for diverse examples") 
    print("   - Enhanced context building for large context windows")
    print("   - Gemini 1M context window optimization")
    print("   - Powered by Google Gemini 2.5 Flash")
    print("\n✅ Use with app_simple_gemini.py for full functionality")


if __name__ == "__main__":
    main()