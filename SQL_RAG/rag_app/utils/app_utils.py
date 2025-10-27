#!/usr/bin/env python3
"""
App Utility Functions
Pure utility functions extracted from app_simple_gemini.py for better organization
"""

from typing import List, Dict
from langchain_core.documents import Document


def estimate_token_count(text: str) -> int:
    """Rough estimation of token count (4 chars ≈ 1 token)."""
    return len(text) // 4


def calculate_context_utilization(docs: List[Document], query: str) -> Dict:
    """Calculate context utilization for Gemini's 1M token window."""
    GEMINI_MAX_TOKENS = 1000000  # 1M token context window
    
    # Estimate tokens
    query_tokens = estimate_token_count(query)
    context_tokens = sum(estimate_token_count(doc.page_content) for doc in docs)
    total_input_tokens = query_tokens + context_tokens
    
    # Calculate utilization
    utilization_percent = (total_input_tokens / GEMINI_MAX_TOKENS) * 100
    
    return {
        'query_tokens': query_tokens,
        'context_tokens': context_tokens,
        'total_input_tokens': total_input_tokens,
        'utilization_percent': min(utilization_percent, 100),  # Cap at 100%
        'chunks_used': len(docs),
        'avg_tokens_per_chunk': context_tokens / len(docs) if docs else 0
    }


def safe_get_value(row, column: str, default: str = '') -> str:
    """Safely get value from dataframe row, handling missing/empty values"""
    try:
        value = row.get(column, default)
        import pandas as pd
        if pd.isna(value) or value is None:
            return default
        return str(value).strip()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"safe_get_value fallback for column '{column}': {e}")
        return default


def get_user_session_id() -> str:
    """
    Get or create a unique user session ID for conversation management.
    
    Returns:
        str: Unique user session identifier
    """
    try:
        import streamlit as st
        import hashlib
        import time
        
        if 'user_session_id' not in st.session_state:
            # Create a unique session ID based on timestamp and random component
            timestamp = str(time.time())
            random_component = str(hash(timestamp + str(id(st.session_state))))
            
            # Create hash for shorter, more manageable ID
            session_content = f"{timestamp}_{random_component}"
            hash_object = hashlib.md5(session_content.encode())
            st.session_state.user_session_id = f"user_{hash_object.hexdigest()[:16]}"
            
            logger = logging.getLogger(__name__)
            logger.info(f"Generated new user session ID: {st.session_state.user_session_id}")
        
        return st.session_state.user_session_id
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating session ID: {e}")
        return f"user_fallback_{int(time.time())}"


def calculate_conversation_tokens(chat_messages: List[Dict]) -> Dict:
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


def _fast_extract_tables(text: str) -> List[str]:
    """Fast table extraction from SQL-like text"""
    import re
    
    # Common table name patterns in SQL
    patterns = [
        r'FROM\s+(\w+)',           # FROM table_name
        r'JOIN\s+(\w+)',           # JOIN table_name
        r'INTO\s+(\w+)',           # INSERT INTO table_name
        r'UPDATE\s+(\w+)',         # UPDATE table_name
        r'CREATE\s+TABLE\s+(\w+)', # CREATE TABLE table_name
    ]
    
    tables = set()
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        tables.update(matches)
    
    # Remove common SQL keywords that might be matched
    sql_keywords = {'SELECT', 'WHERE', 'ORDER', 'GROUP', 'HAVING', 'LIMIT', 'DISTINCT'}
    tables = [table for table in tables if table.upper() not in sql_keywords]
    
    return list(tables)


def detect_agent_type(user_input: str) -> tuple:
    """
    Detect agent keyword and extract the actual question
    
    Args:
        user_input: Raw user input string
        
    Returns:
        Tuple of (agent_type, cleaned_question) where agent_type is None for normal queries
    """
    user_input = user_input.strip()
    
    if user_input.startswith("@explain"):
        question = user_input[8:].strip()  # Remove "@explain" prefix
        return "explain", question
    elif user_input.startswith("@create"):
        question = user_input[7:].strip()  # Remove "@create" prefix
        return "create", question
    elif user_input.startswith("@schema"):
        question = user_input[7:].strip()  # Remove "@schema" prefix
        return "schema", question
    else:
        return None, user_input


def detect_chat_agent_type(user_input: str) -> tuple:
    """
    Chat-specific agent detection with @longanswer support
    
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
    elif user_input.startswith("@schema"):
        question = user_input[7:].strip()  # Remove "@schema" prefix
        return "schema", question
    elif user_input.startswith("@longanswer"):
        question = user_input[11:].strip()  # Remove "@longanswer" prefix
        return "longanswer", question
    else:
        return None, user_input  # Default to concise responses


def get_agent_indicator(agent_type: str) -> str:
    """Get UI indicator for active agent"""
    if agent_type == "explain":
        return "🔍 Explain Agent"
    elif agent_type == "create":
        return "⚡ Create Agent"
    elif agent_type == "schema":
        return "🗂️ Schema Agent"
    else:
        return "💬 Chat"


def get_chat_agent_indicator(agent_type: str) -> str:
    """Get UI indicator for chat-specific agents"""
    if agent_type == "explain":
        return "🔍 Explain Agent"
    elif agent_type == "create":
        return "⚡ Create Agent"
    elif agent_type == "schema":
        return "🗂️ Schema Agent"
    elif agent_type == "longanswer":
        return "📖 Detailed Answer"
    else:
        return "💬 Concise Chat"


def calculate_pagination(total_queries: int, page_size: int = 15) -> Dict:
    """Calculate pagination parameters"""
    import math
    
    if total_queries <= 0:
        return {
            'total_pages': 0,
            'page_size': page_size,
            'has_multiple_pages': False,
            'total_queries': 0
        }
    
    total_pages = math.ceil(total_queries / page_size)
    
    return {
        'total_pages': total_pages,
        'page_size': page_size,
        'has_multiple_pages': total_pages > 1,
        'total_queries': total_queries
    }


def get_page_slice(df, page_num: int, page_size: int = 15):
    """Get a slice of dataframe for the given page"""
    import pandas as pd
    
    if not isinstance(df, pd.DataFrame):
        return df
    
    start_idx = (page_num - 1) * page_size
    end_idx = start_idx + page_size
    return df.iloc[start_idx:end_idx]


def get_page_info(page_num: int, total_queries: int, page_size: int = 15) -> Dict:
    """Get page information for pagination"""
    import math
    
    total_pages = math.ceil(total_queries / page_size) if total_queries > 0 else 0
    start_idx = (page_num - 1) * page_size
    end_idx = min(page_num * page_size, total_queries)
    
    return {
        'current_page': page_num,
        'total_pages': total_pages,
        'start_idx': start_idx,
        'end_idx': end_idx,
        'has_prev': page_num > 1,
        'has_next': page_num < total_pages
    }


def auto_save_conversation():
    """
    Auto-save the current conversation if conversation management is available.
    This is called after each assistant response to keep conversations persisted.
    """
    import streamlit as st
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Import conversation manager
    try:
        from core.conversation_manager import get_conversation_manager
        CONVERSATION_MANAGER_AVAILABLE = True
    except ImportError:
        CONVERSATION_MANAGER_AVAILABLE = False
    
    if not CONVERSATION_MANAGER_AVAILABLE:
        return
    
    # Only auto-save if we have messages and conversation manager is ready
    if (not st.session_state.get('chat_messages') or 
        'conversation_manager' not in st.session_state):
        return
    
    try:
        user_session_id = get_user_session_id()
        conv_id = st.session_state.get('current_conversation_id')
        
        # Auto-save conversation
        saved_id, success = st.session_state.conversation_manager.save_conversation(
            messages=st.session_state.chat_messages,
            user_session_id=user_session_id,
            conversation_id=conv_id
        )
        
        if success:
            st.session_state.current_conversation_id = saved_id
            logger.debug(f"Auto-saved conversation: {saved_id}")
        else:
            logger.warning("Auto-save failed")
            
    except Exception as e:
        logger.error(f"Auto-save error: {e}")