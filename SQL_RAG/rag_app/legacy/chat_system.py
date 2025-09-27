#!/usr/bin/env python3
"""
Chat system functionality for SQL RAG Streamlit application.
Extracted from app_simple_gemini.py for better modularity.
"""

import streamlit as st
import time
import logging
from typing import Any, Dict, List, Optional, Tuple
from langchain_core.documents import Document

from .config import CHAT_DEFAULT_PROMPT_INSTRUCTION
from .utils import estimate_token_count
from gemini_client import GeminiClient
from schema_agent import SchemaAgent, handle_schema_query

# Configure logging
logger = logging.getLogger(__name__)


def detect_chat_agent_type(user_input: str) -> Tuple[Optional[str], str]:
    """
    Chat-specific agent detection with @longanswer and @schema support
    
    Args:
        user_input: Raw user input string
        
    Returns:
        Tuple of (agent_type, cleaned_question) where agent_type is None for concise responses
    """
    user_input = user_input.strip()
    
    if user_input.startswith("@explain"):
        question = user_input[8:].strip()  # Remove "@explain" prefix
        return "explain", question
    elif user_input.startswith("@create"):
        question = user_input[7:].strip()  # Remove "@create" prefix
        return "create", question
    elif user_input.startswith("@longanswer"):
        question = user_input[11:].strip()  # Remove "@longanswer" prefix
        return "longanswer", question
    elif user_input.startswith("@schema"):
        question = user_input[7:].strip()  # Remove "@schema" prefix
        return "schema", question
    else:
        return None, user_input  # Default to concise responses


def get_agent_indicator(agent_type: Optional[str]) -> str:
    """Get UI indicator for active agent"""
    if agent_type == "explain":
        return "🔍 Explain Agent"
    elif agent_type == "create":
        return "⚡ Create Agent"
    else:
        return "💬 Chat"


def get_chat_agent_indicator(agent_type: Optional[str]) -> str:
    """Get UI indicator for chat-specific agents"""
    if agent_type == "explain":
        return "🔍 Explain Agent"
    elif agent_type == "create":
        return "⚡ Create Agent"
    elif agent_type == "longanswer":
        return "📖 Detailed Answer"
    elif agent_type == "schema":
        return "🗂️ Schema Explorer"
    else:
        return "💬 Concise Chat"


def get_chat_prompt_template(agent_type: Optional[str], question: str, schema_section: str, conversation_section: str, context: str) -> str:
    """
    Get chat-specific prompt template with concise default responses
    
    Args:
        agent_type: Agent specialization type ("explain", "create", "longanswer", or None)
        question: User question
        schema_section: Database schema information
        conversation_section: Previous conversation context
        context: Retrieved SQL examples context
        
    Returns:
        Formatted prompt string optimized for chat interface
    """
    
    if agent_type == "explain":
        # Explanation Agent - Keep detailed explanations for learning
        return f"""You are a SQL Explanation Expert. Provide detailed, educational explanations of SQL queries, concepts, and database operations.
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

Focus on education and understanding.

Explanation:"""
    
    elif agent_type == "create":
        # Creation Agent - Keep detailed for SQL generation
        return f"""You are a SQL Creation Expert. Generate efficient, working SQL queries from natural language requirements.
{schema_section}
{conversation_section}
{context}

Current Requirement: {question}

As a Creation Expert, provide a solution that:
1. Generates working SQL code that meets the specified requirements
2. Uses appropriate table structures and relationships from the schema
3. Follows SQL best practices and performance considerations
4. References similar patterns from the context examples when applicable
5. Includes clear comments explaining the approach

Focus on creating practical, efficient SQL solutions.

SQL Solution:"""
    
    elif agent_type == "longanswer":
        # Long Answer Agent - Comprehensive detailed responses
        return f"""You are a comprehensive SQL expert. Provide detailed, thorough analysis using the provided schema, context, and conversation history.
{schema_section}
{conversation_section}
{context}

Current Question: {question}

Provide a comprehensive, detailed answer that:
1. Thoroughly addresses all aspects of the user's question
2. References multiple relevant examples from the context when applicable
3. Uses the database schema extensively to explain relationships and structures
4. Builds extensively on previous conversation context
5. Explains advanced SQL concepts, patterns, and best practices
6. Provides multiple approaches or alternatives when relevant
7. Includes detailed explanations of the reasoning behind recommendations
8. Covers edge cases and considerations

Focus on providing complete, in-depth analysis and guidance.

Detailed Answer:"""
    
    else:
        # Default behavior - Concise 2-3 sentence responses for chat
        return f"""You are a SQL expert assistant. Provide concise, helpful answers in 2-3 sentences that directly address the user's question.
{schema_section}
{conversation_section}
{context}

Current Question: {question}

Provide a brief, focused answer that:
1. Directly answers the user's question in 2-3 sentences
2. References the most relevant example from the context if applicable
3. Uses the database schema when needed for table relationships
4. Builds on previous conversation context when relevant

Keep your response concise and to the point.

Answer:"""


def answer_question_chat_mode(
    question: str, 
    vector_store, 
    k: int = 100,
    schema_manager=None,
    conversation_context: str = "",
    agent_type: Optional[str] = None,
    schema_agent: Optional[SchemaAgent] = None
) -> Optional[Tuple[str, List[Document], Dict[str, Any]]]:
    """
    Chat-specific RAG function with concise default responses and schema agent support
    
    Args:
        question: User question
        vector_store: Pre-loaded FAISS vector store
        k: Number of similar documents to retrieve
        schema_manager: Optional SchemaManager for smart schema injection
        conversation_context: Previous conversation history for context continuity
        agent_type: Chat agent specialization type ("explain", "create", "longanswer", "schema", or None for concise)
        schema_agent: Optional SchemaAgent for database schema exploration
        
    Returns:
        Tuple of (answer, source_documents, token_usage) or None if failed
    """
    
    try:
        # Handle schema queries directly with schema agent
        if agent_type == "schema":
            if schema_agent and schema_agent.is_available():
                logger.info(f"Processing schema query: {question}")
                
                # Generate schema response
                schema_start = time.time()
                answer = handle_schema_query(question, schema_agent)
                schema_time = time.time() - schema_start
                
                # Create minimal token usage tracking for schema queries
                prompt_tokens = estimate_token_count(question)
                completion_tokens = estimate_token_count(answer)
                total_tokens = prompt_tokens + completion_tokens
                
                token_usage = {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'search_method': 'schema',
                    'retrieval_time': 0.0,  # No vector retrieval for schema queries
                    'generation_time': schema_time,
                    'documents_retrieved': 0,
                    'documents_processed': 0,
                    'agent_type': 'schema',
                    'mode': 'chat_schema',
                    'schema_filtering': {'enabled': True, 'schema_available': True}
                }
                
                logger.info(f"Schema query processed in {schema_time:.2f}s")
                return answer, [], token_usage  # Return empty source documents for schema queries
            else:
                # Schema agent not available
                error_msg = ("❌ **Schema Explorer Unavailable**\n\n"
                           "The schema explorer is not available. Please ensure the schema CSV file is loaded.")
                return error_msg, [], {'agent_type': 'schema', 'error': 'schema_agent_unavailable'}
        
        # Continue with regular RAG processing for non-schema queries
        # Step 1: Retrieve relevant documents using vector search
        retrieval_start = time.time()
        docs = vector_store.similarity_search(question, k=k)
        retrieval_time = time.time() - retrieval_start
        
        # Step 2: Build context from retrieved documents
        # Use simple context building for chat (keep it fast and focused)
        context = f"Question: {question}\n\nRelevant SQL examples:\n\n"
        for i, doc in enumerate(docs, 1):
            context += f"Example {i}:\n{doc.page_content}\n\n"
        
        # Step 3: Handle schema injection if available
        relevant_schema = ""
        schema_info = {}
        
        if schema_manager:
            try:
                # Get relevant schema for the question and context
                relevant_schema_data = schema_manager.get_relevant_schema(
                    question=question,
                    context_chunks=[doc.page_content for doc in docs],
                    max_tables=10  # Reasonable limit for chat responses
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
        
        # Step 4: Generate answer using LLM with chat-specific prompts
        logger.info(f"Generating chat response...")
        
        # Build prompt sections
        schema_section = f"\nDatabase Schema (relevant tables):\n{relevant_schema}\n" if relevant_schema else ""
        conversation_section = f"\nPrevious conversation:\n{conversation_context}\n" if conversation_context.strip() else ""
        
        # Use chat-specific prompt template
        prompt = get_chat_prompt_template(
            agent_type=agent_type,
            question=question,
            schema_section=schema_section,
            conversation_section=conversation_section,
            context=context
        )
        
        # Initialize LLM and generate response
        llm = GeminiClient(model="gemini-2.5-flash")  # Use fast model for chat
        
        generation_start = time.time()
        answer = llm.invoke(prompt)
        generation_time = time.time() - generation_start
        
        # Calculate token usage
        prompt_tokens = estimate_token_count(prompt)
        completion_tokens = estimate_token_count(answer)
        total_tokens = prompt_tokens + completion_tokens
        
        # Chat-specific token usage tracking
        token_usage = {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'search_method': 'vector',  # Chat uses simple vector search
            'retrieval_time': retrieval_time,
            'generation_time': generation_time,
            'documents_retrieved': len(docs),
            'documents_processed': len(docs),
            'agent_type': agent_type,
            'mode': 'chat',  # Indicator that this is chat mode
            'schema_filtering': schema_info
        }
        
        logger.info(f"Chat response generated successfully in {generation_time:.2f}s")
        return answer, docs, token_usage
        
    except Exception as e:
        logger.error(f"Error in chat mode: {e}", exc_info=True)
        return None


def calculate_conversation_tokens(chat_messages):
    """Calculate total tokens used in the conversation including context"""
    total_conversation_tokens = 0
    total_response_tokens = 0
    total_context_tokens = 0
    
    for msg in chat_messages:
        # Count message content tokens
        content_tokens = estimate_token_count(msg.get('content', ''))
        total_conversation_tokens += content_tokens
        
        # Count response tokens from API usage
        if msg.get('token_usage'):
            response_tokens = msg['token_usage'].get('total_tokens', 0)
            total_response_tokens += response_tokens
            
            # Count context tokens from retrieved sources
            if msg.get('sources'):
                context_tokens = sum(estimate_token_count(doc.page_content) for doc in msg['sources'])
                total_context_tokens += context_tokens
    
    return {
        'conversation_tokens': total_conversation_tokens,
        'response_tokens': total_response_tokens,
        'context_tokens': total_context_tokens,
        'total_tokens': total_conversation_tokens + total_context_tokens,
        'utilization_percent': min((total_conversation_tokens + total_context_tokens) / 1000000 * 100, 100)
    }


def render_chat_message(msg, is_user=True):
    """Render a single chat message using Streamlit's native chat components"""
    agent_type = msg.get('agent_type')
    content = msg.get('content', '')
    
    # Use Streamlit's native chat message component
    role = "user" if is_user else "assistant"
    
    with st.chat_message(role):
        if not is_user:
            # Show agent indicator for assistant messages
            agent_indicator = get_chat_agent_indicator(agent_type)
            st.caption(f"🤖 {agent_indicator}")
        else:
            # Show agent indicator for user messages if they used a keyword
            if agent_type:
                agent_indicator = get_chat_agent_indicator(agent_type)
                st.caption(f"🎯 {agent_indicator}")
        
        # Display the message content
        st.markdown(content)
        
        # Show sources for assistant messages
        if not is_user and msg.get('sources'):
            with st.expander(f"📚 View {len(msg['sources'])} Source(s)", expanded=False):
                for j, doc in enumerate(msg['sources'], 1):
                    st.markdown(f"**📄 Source {j}:**")
                    st.code(doc.page_content, language="sql")
                    if j < len(msg['sources']):
                        st.divider()


def display_chat_welcome():
    """Display the welcome message for the chat interface"""
    st.markdown("### 👋 Welcome to SQL RAG Chat!")
    st.markdown("Ask questions about your SQL queries using natural language.")
    
    st.info("**💡 Chat Keywords:**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.success("**Default:** 💬 Concise 2-3 sentence responses")
        st.info("**@explain** 🔍 Detailed explanations for learning")
        st.warning("**@create** ⚡ SQL code generation with examples")
    with col2:
        st.error("**@longanswer** 📖 Comprehensive detailed analysis")
        st.markdown("**@schema** 🗂️ Database schema exploration")
    
    st.markdown("**📋 Schema Examples:**")
    st.code("@schema what tables have customer_id column")
    st.code("@schema what columns are in customers table")
    
    st.markdown("---")


def display_chat_header():
    """Display the chat page header with context utilization"""
    # Calculate real-time token usage
    token_stats = calculate_conversation_tokens(st.session_state.get('chat_messages', []))
    
    # Header with context utilization
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("💬 SQL RAG Chat")
        st.caption("Powered by Google Gemini 2.5 Flash")
    
    with col2:
        # Context utilization progress bar
        utilization = token_stats['utilization_percent']
        if utilization < 50:
            color = "🟢"
            status = "Good"
        elif utilization < 80:
            color = "🟡" 
            status = "Moderate"
        else:
            color = "🔴"
            status = "High"
        
        st.metric(
            f"{color} Context Usage", 
            f"{utilization:.1f}%",
            f"{token_stats['total_tokens']:,} tokens"
        )
    
    with col3:
        st.metric(
            "💬 Messages", 
            len(st.session_state.get('chat_messages', [])),
            f"Remaining: {1000000 - token_stats['total_tokens']:,}"
        )
    
    # Progress bar for context utilization
    st.progress(utilization / 100)
    st.divider()
    
    return token_stats


def display_session_statistics(chat_messages):
    """Display detailed session statistics"""
    stats = calculate_conversation_tokens(chat_messages)
    
    st.markdown("### 📊 Session Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Conversation Tokens",
            f"{stats['conversation_tokens']:,}",
            "Messages only"
        )
    
    with col2:
        st.metric(
            "Context Tokens", 
            f"{stats['context_tokens']:,}",
            "Retrieved sources"
        )
    
    with col3:
        st.metric(
            "API Response Tokens",
            f"{stats['response_tokens']:,}",
            "Gemini API usage"
        )
    
    with col4:
        remaining = 1000000 - stats['total_tokens']
        st.metric(
            "Remaining Capacity",
            f"{remaining:,}",
            f"{100 - stats['utilization_percent']:.1f}% free"
        )


def create_chat_page(vector_store, csv_data):
    """Create ChatGPT-like chat conversation page with Gemini mode"""
    
    # Initialize chat messages in session state
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    # Display header with token usage
    token_stats = display_chat_header()
    
    # Display existing messages using native Streamlit chat components
    if st.session_state.chat_messages:
        for msg in st.session_state.chat_messages:
            if msg['role'] == 'user':
                render_chat_message(msg, is_user=True)
            else:
                render_chat_message(msg, is_user=False)
    else:
        # Display welcome message
        display_chat_welcome()
    
    # Add clear conversation button
    if st.session_state.chat_messages:
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.chat_messages = []
            st.session_state.token_usage = []
            st.rerun()
        st.markdown("---")
    
    # Use Streamlit's native chat input
    user_input = st.chat_input(
        placeholder="Ask about SQL queries, joins, optimizations... Use @explain, @create, @longanswer, or @schema for specialized responses"
    )
    
    # Process new message
    if user_input:
        # Detect chat agent type (includes @longanswer)
        agent_type, actual_question = detect_chat_agent_type(user_input.strip())
        
        # Add user message with agent info
        st.session_state.chat_messages.append({
            'role': 'user',
            'content': user_input.strip(),
            'agent_type': agent_type,
            'actual_question': actual_question
        })
        
        # Rerun to display the new message and trigger response generation
        st.rerun()
    
    # Generate response if last message was from user and no response yet
    if (st.session_state.chat_messages and 
        st.session_state.chat_messages[-1]['role'] == 'user' and
        (len(st.session_state.chat_messages) == 1 or 
         st.session_state.chat_messages[-2]['role'] == 'assistant')):
        
        last_user_msg = st.session_state.chat_messages[-1]
        agent_type = last_user_msg.get('agent_type')
        actual_question = last_user_msg.get('actual_question', last_user_msg['content'])
        
        # Get conversation context (exclude the message we're responding to)
        conversation_context = ""
        for msg in st.session_state.chat_messages[:-1]:
            if msg['role'] == 'user':
                conversation_context += f"User: {msg['content']}\n"
            else:
                conversation_context += f"Assistant: {msg['content']}\n"
        
        # Generate response using chat-specific function
        agent_indicator = get_chat_agent_indicator(agent_type)
        with st.spinner(f"Generating response with {agent_indicator}..."):
            try:
                result = answer_question_chat_mode(
                    question=actual_question,
                    vector_store=vector_store,
                    k=100,  # Use high k for comprehensive retrieval
                    schema_manager=st.session_state.get('schema_manager'),
                    conversation_context=conversation_context,
                    agent_type=agent_type,
                    schema_agent=st.session_state.get('schema_agent')
                )
                
                if result:
                    answer, sources, token_usage = result
                    
                    # Add assistant response with agent info
                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': answer,
                        'sources': sources,
                        'token_usage': token_usage,
                        'agent_type': agent_type
                    })
                    
                    # Track token usage
                    if 'token_usage' not in st.session_state:
                        st.session_state.token_usage = []
                    st.session_state.token_usage.append(token_usage)
                    
                else:
                    # Add error message to chat
                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': "❌ I apologize, but I encountered an error generating a response. Please try again.",
                        'sources': [],
                        'token_usage': {},
                        'agent_type': agent_type
                    })
                    
            except Exception as e:
                # Add error message to chat
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': f"❌ Error: {str(e)}. Please try rephrasing your question.",
                    'sources': [],
                    'token_usage': {},
                    'agent_type': agent_type
                })
        
        # Rerun to show new messages
        st.rerun()
    
    # Show detailed token breakdown at bottom if there are messages
    if st.session_state.chat_messages:
        st.divider()
        display_session_statistics(st.session_state.chat_messages)