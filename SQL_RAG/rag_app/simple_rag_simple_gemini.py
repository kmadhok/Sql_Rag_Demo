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
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

# Load environment variables from .env when available (for GEMINI_API_KEY, etc.)
try:
    from dotenv import load_dotenv, find_dotenv
    _env_path = find_dotenv(usecwd=True)
    if _env_path:
        load_dotenv(_env_path, override=False)
        logging.getLogger(__name__).info(f"Loaded environment from {_env_path}")
except Exception as _e:
    logging.getLogger(__name__).debug(f"dotenv not loaded: {_e}")

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

# Import SQL validation functionality
try:
    from core.sql_validator import SQLValidator, ValidationLevel, validate_sql_query
    SQL_VALIDATION_AVAILABLE = True
except ImportError:
    logger.warning("SQL validation not available - check core/sql_validator.py")
    SQL_VALIDATION_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug Logging Utility for SQL Validation Pipeline
class DebugLogger:
    """Enhanced debugging utility for SQL validation pipeline"""
    
    def __init__(self):
        self.debug_file = Path("debug_logs.md")
        self.session_start = datetime.now()
        self.step_counter = 0
        
    def write_header(self, user_question: str):
        """Write debug session header"""
        self.step_counter = 0
        header = f"""# SQL Validation Debug Session
**Session Started**: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}
**User Question**: "{user_question}"

## Pipeline Trace

"""
        with open(self.debug_file, 'w') as f:
            f.write(header)
        logger.info(f"🐛 Debug session started - logging to {self.debug_file}")
    
    def log_step(self, step_name: str, content: Any, details: Dict = None):
        """Log a pipeline step with content and details"""
        self.step_counter += 1
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # Format content based on type
        if isinstance(content, str):
            formatted_content = content
        elif isinstance(content, (list, dict)):
            formatted_content = json.dumps(content, indent=2, default=str)[:2000] + "..." if len(str(content)) > 2000 else json.dumps(content, indent=2, default=str)
        else:
            formatted_content = str(content)
        
        log_entry = f"""
### Step {self.step_counter}: {step_name}
**Timestamp**: {timestamp}

**Content**:
```
{formatted_content}
```
"""
        
        if details:
            log_entry += f"""
**Details**:
```json
{json.dumps(details, indent=2, default=str)}
```
"""
        
        with open(self.debug_file, 'a') as f:
            f.write(log_entry)
        
        logger.info(f"🐛 Step {self.step_counter}: {step_name}")
        
    def log_schema_injection(self, tables_identified: List[str], schema_content: str):
        """Log schema injection details"""
        self.log_step("Schema Injection", schema_content, {
            "tables_identified": tables_identified,
            "schema_length": len(schema_content),
            "tables_count": len(tables_identified)
        })
    
    def log_sql_validation(self, sql: str, validation_result: Any):
        """Log SQL validation results"""
        validation_details = {
            "is_valid": getattr(validation_result, 'is_valid', 'Unknown'),
            "errors": getattr(validation_result, 'errors', []),
            "warnings": getattr(validation_result, 'warnings', []),
            "tables_found": list(getattr(validation_result, 'tables_found', [])),
            "columns_found": list(getattr(validation_result, 'columns_found', []))
        }
        
        self.log_step("SQL Validation", sql, validation_details)
    
    def log_error(self, error_type: str, error_message: str, context: Dict = None):
        """Log validation errors"""
        self.log_step(f"ERROR: {error_type}", error_message, context or {})

# Global debug logger instance
debug_logger = DebugLogger()

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
            return f"""You are a BigQuery SQL Creation Expert. Your role is to generate efficient, working BigQuery SQL queries from natural language requirements. Use the provided schema with data type guidance, context, and conversation history to create optimal SQL solutions.

CRITICAL BIGQUERY REQUIREMENTS:
- Always use fully-qualified table names: `project.dataset.table` (aliases allowed after qualification)
- Use BigQuery Standard SQL syntax
- For TIMESTAMP columns: Use TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL X DAY) - NOT DATE_SUB with CURRENT_DATE()
- For DATE columns: Use DATE_SUB(CURRENT_DATE(), INTERVAL X DAY)
- NEVER mix TIMESTAMP and DATETIME types in comparisons
- Use proper data type casting: CAST(column AS STRING), CAST(value AS TIMESTAMP)
- Pay attention to column data types from the schema to avoid type mismatch errors

{schema_section}
{conversation_section}
{context}

Current Requirement: {question}

As a BigQuery Creation Expert, provide a comprehensive solution that:
1. Generates working BigQuery SQL code that meets the specified requirements
2. Uses appropriate table structures and column data types from the schema
3. Follows BigQuery SQL best practices and avoids common type errors
4. Uses correct BigQuery functions for each data type (especially TIMESTAMP vs DATE)
5. References similar patterns from the context examples when applicable
6. Builds on previous conversation context when relevant
7. Includes clear comments explaining the approach and data type considerations
8. Considers edge cases and data integrity
9. Uses proper BigQuery date/time functions to avoid TIMESTAMP/DATETIME conflicts

Focus on creating practical, error-free BigQuery SQL solutions that respect column data types.

SQL Solution:"""
        else:
            return f"""You are a BigQuery SQL Creation Expert. Generate efficient BigQuery SQL queries from requirements using the provided schema with data types, examples, and conversation history.

IMPORTANT: Use BigQuery syntax - TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL X DAY) for TIMESTAMP columns, not DATE_SUB. Pay attention to column data types to avoid type mismatches.

{schema_section}
{conversation_section}
{context}

Current Requirement: {question}

Create working BigQuery SQL code with proper data types and clear comments.

SQL Solution:"""
    
    else:
        # Default behavior - General SQL assistance
        if gemini_mode:
            return f"""You are a BigQuery SQL expert analyzing a comprehensive set of examples. Use the provided schema with data type guidance, context, and conversation history to give a detailed, helpful answer. When writing SQL for BigQuery, always use proper data types and functions.

BIGQUERY REQUIREMENTS: Use TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL X DAY) for TIMESTAMP columns, not DATE_SUB. Always use fully-qualified table names (project.dataset.table) and respect column data types.

{schema_section}
{conversation_section}
{context}

Current Question: {question}

Provide a comprehensive answer that:
1. Directly addresses the user's current question
2. References relevant examples from the context
3. Uses the database schema and respects column data types
4. Builds on previous conversation when relevant
5. Explains key BigQuery SQL concepts and patterns
6. Suggests BigQuery best practices when applicable

Answer:"""
        else:
            return f"""You are a BigQuery SQL expert. Based on the provided database schema with data types, SQL examples, and conversation history, answer the user's question clearly and concisely.

IMPORTANT: Use BigQuery syntax with proper data types - TIMESTAMP_SUB for TIMESTAMP columns, not DATE_SUB.

{schema_section}
{conversation_section}
{context}

Current Question: {question}

Answer:"""


def build_lookml_context(question: str, lookml_safe_join_map: dict) -> str:
    """
    Build LookML context based on the user's question to enhance SQL generation
    
    Args:
        question: User's question
        lookml_safe_join_map: LookML safe-join map data
        
    Returns:
        LookML context string with relevant join information
    """
    if not lookml_safe_join_map:
        return ""
    
    question_lower = question.lower()
    explores = lookml_safe_join_map.get('explores', {})
    join_graph = lookml_safe_join_map.get('join_graph', {})
    
    # Extract table names mentioned in the question
    mentioned_tables = []
    for table in join_graph.keys():
        if table in question_lower:
            mentioned_tables.append(table)
    
    # If no specific tables mentioned, use common ecommerce patterns
    if not mentioned_tables:
        if any(word in question_lower for word in ['user', 'customer', 'buyer']):
            mentioned_tables.append('users')
        if any(word in question_lower for word in ['order', 'purchase', 'transaction']):
            mentioned_tables.extend(['orders', 'order_items'])
        if any(word in question_lower for word in ['product', 'item', 'merchandise']):
            mentioned_tables.append('products')
    
    if not mentioned_tables:
        return ""
    
    # Build context for relevant explores and joins
    context_parts = []
    context_parts.append("🔗 **LookML Join Information:**")
    
    # Find the best explore that includes the mentioned tables
    best_explore = None
    max_table_coverage = 0
    
    for explore_name, explore_data in explores.items():
        available_tables = set([explore_name] + list(explore_data.get('joins', {}).keys()))
        covered_tables = set(mentioned_tables).intersection(available_tables)
        if len(covered_tables) > max_table_coverage:
            max_table_coverage = len(covered_tables)
            best_explore = explore_name
    
    if best_explore and best_explore in explores:
        explore_data = explores[best_explore]
        context_parts.append(f"\n**Recommended Explore:** `{best_explore}` ({explore_data.get('label', best_explore)})")
        
        # Add join conditions for mentioned tables
        joins = explore_data.get('joins', {})
        for table in mentioned_tables:
            if table in joins:
                join_info = joins[table]
                sql_on = join_info.get('sql_on', '')
                join_type = join_info.get('join_type', 'left_outer')
                relationship = join_info.get('relationship', 'many_to_one')
                
                context_parts.append(f"\n**{table} Join:**")
                context_parts.append(f"  SQL: `{sql_on}`")
                context_parts.append(f"  Type: {join_type}")
                context_parts.append(f"  Relationship: {relationship}")
    
    # Add general join graph information
    context_parts.append(f"\n**Available Join Paths:**")
    for table in mentioned_tables:
        if table in join_graph:
            joinable_tables = join_graph[table]
            if joinable_tables:
                context_parts.append(f"  {table} → {', '.join(joinable_tables)}")
    
    return '\n'.join(context_parts) if len(context_parts) > 1 else ""


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
    lookml_safe_join_map=None,
    conversation_context: str = "",
    agent_type: Optional[str] = None,
    sql_validation: bool = False,
    validation_level: ValidationLevel = ValidationLevel.SCHEMA_STRICT,
    excluded_tables: Optional[List[str]] = None,
    user_context: str = ""
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
        lookml_safe_join_map: Optional LookML safe-join map for enhanced SQL generation with accurate join syntax
        conversation_context: Previous conversation history for context continuity
        agent_type: Agent specialization type ("explain", "create", or None for default)
        sql_validation: Enable SQL query validation against schema
        validation_level: Validation strictness level (SYNTAX_ONLY, SCHEMA_BASIC, SCHEMA_STRICT)
        excluded_tables: Optional list of table names to exclude from schema and discourage in SQL
        user_context: Optional user-provided context to prepend to prompt context
        
    Returns:
        Tuple of (answer, source_documents, enhanced_token_usage) or None if failed
    """
    
    try:
        # Debug Logging: Initialize session
        debug_logger.write_header(question)
        debug_logger.log_step("Function Parameters", {
            "question": question,
            "k": k,
            "gemini_mode": gemini_mode,
            "hybrid_search": hybrid_search,
            "query_rewriting": query_rewriting,
            "sql_validation": sql_validation,
            "validation_level": str(validation_level),
            "excluded_tables": excluded_tables,
            "schema_manager_available": schema_manager is not None,
            "lookml_safe_join_map_available": lookml_safe_join_map is not None
        })
        
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
        
        # Debug Logging: Document retrieval
        debug_logger.log_step("Document Retrieval Setup", {
            "search_method": search_method,
            "search_query": search_query,
            "original_question": question,
            "k_documents": k,
            "query_rewritten": search_query != question
        })
        
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
                # Fallback to vector search with timeout and keyword-only backup
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
                embedding_timeout = float(os.getenv('EMBEDDING_TIMEOUT_SECONDS', '15'))
                
                def _do_vector_search():
                    return vector_store.similarity_search(search_query, k=k)
                
                try:
                    with ThreadPoolExecutor(max_workers=1) as ex:
                        fut = ex.submit(_do_vector_search)
                        docs = fut.result(timeout=embedding_timeout)
                    logger.warning("Hybrid retriever unavailable; used vector search fallback")
                except FuturesTimeout:
                    logger.warning(f"Vector search timed out after {embedding_timeout}s (hybrid unavailable). Falling back to keyword-only search.")
                    hr = _initialize_hybrid_retriever(vector_store)
                    if hr:
                        docs = hr.search(search_query, k=k, method='keyword')
                        search_method = 'keyword'
                    else:
                        docs = []
        else:
            # Standard vector search (with timeout + keyword fallback)
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
            embedding_timeout = float(os.getenv('EMBEDDING_TIMEOUT_SECONDS', '15'))
            
            def _do_vector_search():
                return vector_store.similarity_search(search_query, k=k)
            
            try:
                with ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(_do_vector_search)
                    docs = fut.result(timeout=embedding_timeout)
                logger.info(f"Vector search: {len(docs)} documents retrieved")
            except FuturesTimeout:
                logger.warning(f"Vector search timed out after {embedding_timeout}s. Falling back to keyword-only search.")
                if HYBRID_SEARCH_AVAILABLE:
                    hr = _initialize_hybrid_retriever(vector_store)
                    if hr:
                        docs = hr.search(search_query, k=k, method='keyword')
                        search_method = 'keyword'
                        logger.info(f"Keyword fallback: {len(docs)} documents retrieved")
                    else:
                        docs = []
                else:
                    docs = []
        
        retrieval_time = time.time() - start_time
        
        if not docs:
            logger.warning("No relevant documents found")
            return None
        
        logger.info(f"Retrieved {len(docs)} documents in {retrieval_time:.2f}s")
        
        # Debug Logging: Retrieved documents
        debug_logger.log_step("Retrieved Documents", 
                             [{"content": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content, 
                               "metadata": doc.metadata} for doc in docs],
                             {"count": len(docs), "retrieval_time": f"{retrieval_time:.2f}s"})
        
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
                    # Apply exclusions if provided
                    excluded_set = {schema_manager._normalize_table_name(t) for t in (excluded_tables or [])}
                    filtered_tables = [t for t in relevant_tables if schema_manager._normalize_table_name(t) not in excluded_set]

                    # Filter schema to only relevant tables (39K → ~100-500 rows)
                    relevant_schema = schema_manager.get_relevant_schema(filtered_tables)
                    
                    if relevant_schema:
                        # Append exclusion directive if needed
                        if excluded_set:
                            excl_list = ", ".join(sorted(excluded_set))
                            relevant_schema += f"\n\nEXCLUDED TABLES: {excl_list}\nInstruction: Do not reference excluded tables in the SQL."
                        logger.info(f"Smart schema filtering: {len(relevant_tables)} tables identified, schema filtered for injection")
                        
                        # Debug Logging: Schema injection
                        debug_logger.log_schema_injection(relevant_tables, relevant_schema)
                    else:
                        logger.info("No matching schema found for identified tables")
                        debug_logger.log_step("Schema Injection Failed", "No matching schema found", 
                                            {"relevant_tables": relevant_tables})
                else:
                    logger.info("No tables identified from retrieved documents")
                    debug_logger.log_step("Schema Injection Skipped", "No tables identified from documents")
                    
            except Exception as e:
                logger.warning(f"Schema filtering failed, continuing without schema: {e}")
                relevant_schema = ""
        
        # If we have fully-qualified table names, append instruction block to schema
        if schema_manager and relevant_schema:
            try:
                # Recompute relevant tables from question + docs for mapping
                _tables_for_map = schema_manager.extract_tables_from_documents(processed_docs)
                _tables_for_map += schema_manager.extract_tables_from_content(question)
                # Respect exclusions
                excluded_set = {schema_manager._normalize_table_name(t) for t in (excluded_tables or [])}
                _tables_for_map = [t for t in _tables_for_map if schema_manager._normalize_table_name(t) not in excluded_set]
                fqn_map = schema_manager.get_fqn_map(_tables_for_map)
            except Exception:
                fqn_map = {}
            if fqn_map:
                fqn_lines = ["\nBIGQUERY FULLY QUALIFIED TABLES (use in FROM/JOIN):"]
                for t, fqn in fqn_map.items():
                    fqn_lines.append(f"  - {t} -> `{fqn}`")
                fqn_lines.append("\nInstruction: Always reference tables using fully-qualified names above (project.dataset.table). You may use SQL aliases after qualification.")
                relevant_schema = relevant_schema + "\n" + "\n".join(fqn_lines)

        # Prepend user context when provided
        prepend_ctx = ""
        if user_context and user_context.strip():
            prepend_ctx = f"User Context (high priority):\n{user_context.strip()}\n\n"

        if gemini_mode:
            # Build enhanced context for large context windows
            context = prepend_ctx + _build_enhanced_context(processed_docs, question)
        else:
            # Build simple context for standard mode
            context = prepend_ctx + f"Question: {question}\n\nRelevant SQL examples:\n\n"
            for i, doc in enumerate(processed_docs, 1):
                context += f"Example {i}:\n{doc.page_content}\n\n"
        
        # Step 3: Generate answer using LLM
        logger.info(f"Generating answer using {GEMINI_MODEL}...")
        
        # Build prompt with agent specialization, schema injection, LookML joins, and conversation context
        schema_section = f"\n{relevant_schema}\n" if relevant_schema else ""
        
        # Add LookML join information for enhanced SQL generation
        if lookml_safe_join_map and (agent_type == "create" or "join" in question.lower() or "sql" in question.lower()):
            lookml_context = build_lookml_context(question, lookml_safe_join_map)
            if lookml_context:
                schema_section += f"\n{lookml_context}\n"
        
        # Safely include prior conversation if provided
        _conv = conversation_context if isinstance(conversation_context, str) else ""
        conversation_section = f"\nPrevious conversation:\n{_conv}\n" if _conv.strip() else ""
        
        # Use agent-specific prompt template
        prompt = get_agent_prompt_template(
            agent_type=agent_type,
            question=question,
            schema_section=schema_section,
            conversation_section=conversation_section,
            context=context,
            gemini_mode=gemini_mode
        )
        
        # Debug Logging: LLM prompt details
        debug_logger.log_step("LLM Prompt Building", {
            "agent_type": agent_type,
            "schema_section_length": len(schema_section),
            "conversation_section_length": len(conversation_section),
            "context_length": len(context),
            "full_prompt_length": len(prompt),
            "gemini_mode": gemini_mode,
            "model": GEMINI_MODEL
        }, {
            "schema_section": schema_section[:1000] + "..." if len(schema_section) > 1000 else schema_section,
            "full_prompt": prompt[:2000] + "..." if len(prompt) > 2000 else prompt
        })
        
        # Initialize LLM and generate response
        llm = GeminiClient(model=GEMINI_MODEL)
        
        generation_start = time.time()
        answer = llm.invoke(prompt)
        generation_time = time.time() - generation_start
        
        # Debug Logging: LLM response
        debug_logger.log_step("LLM Response", {
            "generation_time": f"{generation_time:.2f}s",
            "response_length": len(answer),
            "model": GEMINI_MODEL
        }, {
            "response": answer[:1500] + "..." if len(answer) > 1500 else answer
        })
        
        # Step 4: SQL Validation (optional)
        validation_result = None
        if sql_validation and SQL_VALIDATION_AVAILABLE:
            try:
                logger.info("Validating generated SQL against schema...")
                validation_start = time.time()
                
                # Debug: Log schema manager availability
                if schema_manager:
                    logger.info(f"🗃️ Schema manager available: {schema_manager.table_count} tables, {schema_manager.column_count} columns")
                else:
                    logger.info("⚠️ No schema manager provided for validation - table/column validation will be limited")
                
                # Debug: Log the SQL content being validated (truncated for readability)
                sql_preview = answer[:200].replace('\n', ' ').strip()
                if len(answer) > 200:
                    sql_preview += "..."
                logger.debug(f"🔍 Validating SQL content: {sql_preview}")
                
                # Use schema manager for validation if available
                validation_result = validate_sql_query(
                    answer, 
                    schema_manager=schema_manager,
                    validation_level=validation_level
                )
                
                validation_time = time.time() - validation_start
                
                if validation_result.is_valid:
                    logger.info(f"✅ SQL validation passed ({len(validation_result.tables_found)} tables, {len(validation_result.columns_found)} columns)")
                else:
                    logger.warning(f"⚠️ SQL validation found {len(validation_result.errors)} errors, {len(validation_result.warnings)} warnings")
                    
                    # Log specific errors
                    for i, error in enumerate(validation_result.errors, 1):
                        logger.warning(f"   Error {i}: {error}")
                    
                    # Log warnings if any
                    for i, warning in enumerate(validation_result.warnings, 1):
                        logger.warning(f"   Warning {i}: {warning}")
                    
                    # Log what was found for debugging
                    if validation_result.tables_found:
                        logger.info(f"   Tables found: {list(validation_result.tables_found)}")
                    if validation_result.columns_found:
                        logger.info(f"   Columns found: {list(validation_result.columns_found)}")
                    
                    # Log suggestions if any
                    for i, suggestion in enumerate(validation_result.suggestions, 1):
                        logger.info(f"   Suggestion {i}: {suggestion}")
                    
                logger.info(f"SQL validation completed in {validation_time:.3f}s")
                
                # Debug Logging: SQL validation details
                debug_logger.log_sql_validation(answer, validation_result)
                
            except Exception as e:
                logger.error(f"SQL validation failed: {e}")
                # Continue without validation
        
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
            'generation_time': generation_time,
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
        
        # Add SQL validation information if available
        if sql_validation and validation_result:
            token_usage.update({
                'sql_validation': {
                    'enabled': True,
                    'is_valid': validation_result.is_valid,
                    'validation_level': validation_result.validation_level.value,
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings,
                    'tables_found': list(validation_result.tables_found),
                    'columns_found': list(validation_result.columns_found),
                    'joins_found': validation_result.joins_found,
                    'suggestions': validation_result.suggestions,
                    'has_errors': validation_result.has_errors,
                    'has_warnings': validation_result.has_warnings,
                    'validation_time': validation_time if 'validation_time' in locals() else 0
                }
            })
        else:
            token_usage['sql_validation'] = {'enabled': False}
        
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
        
        # Debug Logging: Final results summary
        debug_logger.log_step("Final Results", {
            "success": True,
            "answer_length": len(answer.strip()),
            "processed_docs_count": len(processed_docs),
            "total_tokens": total_tokens,
            "validation_passed": validation_result.is_valid if validation_result else "Not validated",
            "generation_time": f"{generation_time:.2f}s"
        })
        
        return answer.strip(), processed_docs, token_usage
        
    except Exception as e:
        logger.error(f"Error in answer_question_simple_gemini: {e}", exc_info=True)
        # Debug Logging: Error case
        debug_logger.log_error("Pipeline Error", str(e), {"exception_type": type(e).__name__})
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
