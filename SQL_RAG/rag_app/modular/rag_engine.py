#!/usr/bin/env python3
"""
Modular RAG Engine - Core RAG functionality for the modular SQL RAG application.
Based on simple_rag_simple_gemini.py with improved modularity.
"""

import time
import logging
import os
import sys
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from modular.config import GEMINI_MODEL, GEMINI_MAX_CONTEXT_TOKENS, SIMILARITY_THRESHOLD
from modular.utils import estimate_token_count

# Configure logging
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Import Gemini client
try:
    from core.gemini_client import GeminiClient, test_gemini_connection
except ImportError:
    logger.error("Could not import gemini_client. Ensure it's in the parent directory.")
    GeminiClient = None
    test_gemini_connection = None

# Import hybrid search functionality
HYBRID_SEARCH_AVAILABLE = False
try:
    from core.hybrid_retriever import HybridRetriever, SearchWeights, HybridSearchResult
    HYBRID_SEARCH_AVAILABLE = True
except ImportError:
    logger.warning("Hybrid search not available - install rank-bm25: pip install rank-bm25")
    HYBRID_SEARCH_AVAILABLE = False

# Import query rewriting functionality
QUERY_REWRITING_AVAILABLE = False
try:
    from core.query_rewriter import QueryRewriter, create_query_rewriter
    QUERY_REWRITING_AVAILABLE = True
except ImportError:
    logger.warning("Query rewriting not available - check simple_query_rewriter.py")
    QUERY_REWRITING_AVAILABLE = False


class RAGEngine:
    """Core RAG engine with Gemini optimization and modular design"""
    
    def __init__(self):
        self._query_rewriter = None
        self._hybrid_retriever = None
    
    def test_gemini_connection(self, model: str = GEMINI_MODEL) -> Tuple[bool, str]:
        """Test connection to Gemini service"""
        if test_gemini_connection is None:
            return False, "Gemini client not available"
        return test_gemini_connection(model=model)
    
    def _extract_documents_from_vector_store(self, vector_store: FAISS) -> List[Document]:
        """Extract all documents from a FAISS vector store for hybrid retriever initialization"""
        try:
            documents = []
            docstore = vector_store.docstore
            
            if hasattr(docstore, '_dict'):
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
    
    def _initialize_hybrid_retriever(self, vector_store: FAISS) -> Optional[HybridRetriever]:
        """Initialize hybrid retriever with vector store and documents"""
        if not HYBRID_SEARCH_AVAILABLE:
            return None
        
        try:
            documents = self._extract_documents_from_vector_store(vector_store)
            
            if not documents:
                logger.warning("No documents extracted - falling back to vector search only")
                return None
            
            hybrid_retriever = HybridRetriever(vector_store, documents)
            logger.info("✅ Hybrid retriever initialized successfully")
            return hybrid_retriever
            
        except Exception as e:
            logger.error(f"Failed to initialize hybrid retriever: {e}")
            return None
    
    def _deduplicate_chunks(self, docs: List[Document], similarity_threshold: float = SIMILARITY_THRESHOLD) -> List[Document]:
        """Remove highly similar chunks to avoid redundant context using Jaccard similarity"""
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
    
    def _prioritize_diverse_content(self, docs: List[Document], query: str) -> List[Document]:
        """Prioritize diverse content types for comprehensive context coverage"""
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
    
    def _build_enhanced_context(self, docs: List[Document], query: str, max_tokens: int = GEMINI_MAX_CONTEXT_TOKENS) -> str:
        """Build enhanced context string optimized for large context windows"""
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
    
    def get_agent_prompt_template(self, agent_type: Optional[str], question: str, schema_section: str, conversation_section: str, context: str, gemini_mode: bool = False) -> str:
        """Get specialized prompt template based on agent type"""
        
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
    
    def answer_question(
        self,
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
        """
        
        try:
            # Step 0: Query rewriting for enhanced retrieval (optional)
            rewrite_data = None
            search_query = question  # Default to original question
            
            if query_rewriting and QUERY_REWRITING_AVAILABLE:
                # Initialize simple query rewriter (cached for performance)
                if self._query_rewriter is None:
                    self._query_rewriter = create_query_rewriter()
                
                try:
                    logger.info(f"Rewriting query for enhanced retrieval: {question[:50]}...")
                    rewrite_data = self._query_rewriter.rewrite_query(question)
                    
                    if rewrite_data['query_changed'] and not rewrite_data['error']:
                        search_query = rewrite_data['rewritten_query']
                        logger.info(f"Using rewritten query: {search_query[:50]}...")
                    else:
                        logger.info(f"Using original query (no changes or error: {rewrite_data.get('error', 'N/A')})")
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
                if self._hybrid_retriever is None:
                    self._hybrid_retriever = self._initialize_hybrid_retriever(vector_store)
                
                if self._hybrid_retriever:
                    # Perform hybrid search
                    hybrid_results = self._hybrid_retriever.hybrid_search(
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
                processed_docs = self._deduplicate_chunks(processed_docs)
                
                # Apply content prioritization for diversity
                processed_docs = self._prioritize_diverse_content(processed_docs, question)
            
            # Step 2.5: Smart schema filtering (extract relevant tables and inject schema)
            relevant_schema = ""
            schema_info = {}
            if schema_manager:
                try:
                    # Get relevant schema for the question and context
                    relevant_schema_data = schema_manager.get_relevant_schema(
                        question=question,
                        context_chunks=[doc.page_content for doc in processed_docs],
                        max_tables=10  # Reasonable limit for responses
                    )
                    
                    if relevant_schema_data:
                        relevant_schema = relevant_schema_data['schema_text']
                        schema_info = {
                            'enabled': True,
                            'relevant_tables': relevant_schema_data['table_count'],
                            'schema_tokens': estimate_token_count(relevant_schema),
                            'total_schema_tables': schema_manager.table_count,
                            'schema_coverage': f"{relevant_schema_data['table_count']}/{schema_manager.table_count}",
                            'schema_available': True
                        }
                    else:
                        schema_info = {'enabled': True, 'schema_available': False}
                        
                except Exception as e:
                    logger.warning(f"Schema injection failed: {e}")
                    schema_info = {'enabled': True, 'schema_available': False, 'error': str(e)}
            else:
                schema_info = {'enabled': False}
            
            if gemini_mode:
                # Build enhanced context for large context windows
                context = self._build_enhanced_context(processed_docs, question)
            else:
                # Build simple context for standard mode
                context = f"Question: {question}\n\nRelevant SQL examples:\n\n"
                for i, doc in enumerate(processed_docs, 1):
                    context += f"Example {i}:\n{doc.page_content}\n\n"
            
            # Step 3: Generate answer using LLM
            logger.info(f"Generating answer using {GEMINI_MODEL}...")
            
            # Build prompt with agent specialization, schema injection, and conversation context
            schema_section = f"\nDatabase Schema (relevant tables):\n{relevant_schema}\n" if relevant_schema else ""
            conversation_section = f"\nPrevious conversation:\n{conversation_context}\n" if conversation_context.strip() else ""
            
            # Use agent-specific prompt template
            prompt = self.get_agent_prompt_template(
                agent_type=agent_type,
                question=question,
                schema_section=schema_section,
                conversation_section=conversation_section,
                context=context,
                gemini_mode=gemini_mode
            )
            
            # Initialize LLM and generate response
            if GeminiClient is None:
                raise Exception("Gemini client not available")
            
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
                'generation_time': generation_time,
                'documents_retrieved': len(docs),
                'documents_processed': len(processed_docs),
                'agent_type': agent_type,
                'schema_filtering': schema_info
            }
            
            # Add query rewriting information if available
            if rewrite_data:
                token_usage.update({
                    'query_rewriting': {
                        'enabled': True,
                        'rewritten_query': rewrite_data['rewritten_query'],
                        'method': rewrite_data['method'],
                        'query_used': search_query,
                        'query_changed': rewrite_data['query_changed'],
                        'error': rewrite_data.get('error')
                    }
                })
            else:
                token_usage['query_rewriting'] = {'enabled': False}
            
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
            logger.error(f"Error in RAG engine: {e}", exc_info=True)
            return None


# Global instance for use throughout the application
rag_engine = RAGEngine()