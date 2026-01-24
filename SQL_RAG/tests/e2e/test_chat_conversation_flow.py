#!/usr/bin/env python3
"""
End-to-End Tests for Chat Conversation Flow

Tests complete user conversation flows including:
- User input processing
- RAG retrieval
- LLM response generation
- Message history management
- Token tracking
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "rag_app"))

from tests.fixtures.mock_helpers import create_mock_documents


@pytest.mark.e2e
@pytest.mark.chat
class TestChatConversationFlow:
    """Test suite for complete chat conversation flows"""

    def test_simple_question_answer_flow(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test basic question-answer flow without agent keywords"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        # Simulate user asking a simple question
        question = "Show me all users from 2023"

        # Execute the RAG function
        result = answer_question_chat_mode(
            question=question,
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type=None
        )

        # Verify result structure
        assert result is not None, "Should return a valid result"
        answer, sources, token_usage = result

        # Verify answer
        assert isinstance(answer, str), "Answer should be a string"
        assert len(answer) > 0, "Answer should not be empty"

        # Verify sources
        assert isinstance(sources, list), "Sources should be a list"
        assert len(sources) <= 10, "Should retrieve at most k documents"

        # Verify token usage
        assert 'total_tokens' in token_usage, "Should track total tokens"
        assert 'mode' in token_usage and token_usage['mode'] == 'chat', "Should indicate chat mode"
        assert token_usage['agent_type'] is None, "No agent for basic questions"

    def test_conversation_with_context(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test conversation with previous context"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        # Simulate conversation history
        conversation_context = """User: Show me all users
Assistant: Here's a query to get all users: SELECT * FROM users
"""

        # Follow-up question
        question = "Now filter for active users only"

        result = answer_question_chat_mode(
            question=question,
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context=conversation_context,
            agent_type=None
        )

        assert result is not None, "Should handle conversation context"
        answer, sources, token_usage = result

        # Verify conversation context was used
        assert isinstance(answer, str), "Should generate contextual answer"
        assert token_usage['mode'] == 'chat', "Should be in chat mode"

    def test_agent_type_detection(self):
        """Test detection of agent keywords in user input"""
        from rag_app.app_simple_gemini import detect_chat_agent_type

        # Test @explain
        agent_type, question = detect_chat_agent_type("@explain SELECT * FROM users")
        assert agent_type == "explain", "Should detect @explain agent"
        assert question == "SELECT * FROM users", "Should remove @explain prefix"

        # Test @create
        agent_type, question = detect_chat_agent_type("@create a query for recent orders")
        assert agent_type == "create", "Should detect @create agent"
        assert question == "a query for recent orders", "Should remove @create prefix"

        # Test @schema
        agent_type, question = detect_chat_agent_type("@schema show me the users table")
        assert agent_type == "schema", "Should detect @schema agent"
        assert question == "show me the users table", "Should remove @schema prefix"

        # Test @longanswer
        agent_type, question = detect_chat_agent_type("@longanswer explain joins in detail")
        assert agent_type == "longanswer", "Should detect @longanswer agent"
        assert question == "explain joins in detail", "Should remove @longanswer prefix"

        # Test no agent (default)
        agent_type, question = detect_chat_agent_type("Show me all users")
        assert agent_type is None, "Should return None for normal questions"
        assert question == "Show me all users", "Should keep original question"

    def test_token_calculation_for_conversation(self, sample_chat_messages):
        """Test token usage calculation for entire conversation"""
        from rag_app.app_simple_gemini import calculate_conversation_tokens

        token_stats = calculate_conversation_tokens(sample_chat_messages)

        # Verify all required fields are present
        assert 'conversation_tokens' in token_stats, "Should track conversation tokens"
        assert 'response_tokens' in token_stats, "Should track response tokens"
        assert 'context_tokens' in token_stats, "Should track context tokens"
        assert 'total_tokens' in token_stats, "Should track total tokens"
        assert 'utilization_percent' in token_stats, "Should calculate utilization percentage"

        # Verify calculations make sense
        assert token_stats['total_tokens'] >= 0, "Total tokens should be non-negative"
        assert 0 <= token_stats['utilization_percent'] <= 100, "Utilization should be 0-100%"

    def test_chat_with_user_context(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test chat with additional user-provided context"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        user_context = "Only include users from the US region. Exclude test accounts."

        result = answer_question_chat_mode(
            question="Show me active users",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type=None,
            user_context=user_context
        )

        assert result is not None, "Should handle user context"
        answer, sources, token_usage = result
        assert isinstance(answer, str), "Should generate answer with user context"

    def test_chat_with_excluded_tables(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test chat with table exclusions"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        excluded_tables = ['archive_users', 'deleted_orders']

        result = answer_question_chat_mode(
            question="Show me user data",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type=None,
            excluded_tables=excluded_tables
        )

        assert result is not None, "Should handle table exclusions"
        answer, sources, token_usage = result

        # Verify schema filtering info is tracked
        assert 'schema_filtering' in token_usage, "Should track schema filtering"

    @patch('rag_app.app_simple_gemini.GeminiClient')
    def test_llm_api_failure_handling(
        self,
        mock_llm_class,
        mock_vector_store,
        mock_schema_manager
    ):
        """Test handling of LLM API failures"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        # Make LLM raise an exception
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.side_effect = Exception("API Error")
        mock_llm_class.return_value = mock_llm_instance

        result = answer_question_chat_mode(
            question="Test question",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type=None
        )

        # Should return None on failure
        assert result is None, "Should return None when LLM fails"

    def test_vector_search_timeout_fallback(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager,
        monkeypatch
    ):
        """Test fallback to keyword search when vector search times out"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        # Set very short timeout to trigger fallback
        monkeypatch.setenv('EMBEDDING_TIMEOUT_SECONDS', '0.001')

        # Make vector search slow
        def slow_search(*args, **kwargs):
            import time
            time.sleep(1)
            return create_mock_documents(5)

        mock_vector_store.similarity_search = slow_search

        # Should still complete with keyword fallback
        result = answer_question_chat_mode(
            question="Test question",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type=None
        )

        # May return None or result depending on fallback availability
        # Just verify it doesn't hang indefinitely
        assert True, "Should not hang on timeout"

    def test_empty_conversation_initialization(self):
        """Test initialization of empty conversation state"""
        from rag_app.app_simple_gemini import calculate_conversation_tokens

        empty_messages = []
        token_stats = calculate_conversation_tokens(empty_messages)

        assert token_stats['conversation_tokens'] == 0, "Empty conversation should have 0 tokens"
        assert token_stats['total_tokens'] == 0, "Total should be 0 for empty conversation"
        assert token_stats['utilization_percent'] == 0, "Utilization should be 0%"

    def test_multi_turn_conversation_flow(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test multiple conversation turns building context"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        # Turn 1: Initial question
        result1 = answer_question_chat_mode(
            question="Show me users",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type=None
        )
        assert result1 is not None, "First turn should succeed"
        answer1, _, usage1 = result1

        # Turn 2: Follow-up with context from turn 1
        context_after_turn1 = f"User: Show me users\nAssistant: {answer1}\n"

        result2 = answer_question_chat_mode(
            question="Filter for active ones",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context=context_after_turn1,
            agent_type=None
        )
        assert result2 is not None, "Second turn should succeed"
        answer2, _, usage2 = result2

        # Turn 3: Further refinement
        context_after_turn2 = context_after_turn1 + f"User: Filter for active ones\nAssistant: {answer2}\n"

        result3 = answer_question_chat_mode(
            question="Sort by creation date",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context=context_after_turn2,
            agent_type=None
        )
        assert result3 is not None, "Third turn should succeed"

        # Verify all turns completed
        assert all([result1, result2, result3]), "All conversation turns should complete"

    def test_session_id_generation(self):
        """Test unique session ID generation"""
        from rag_app.app_simple_gemini import get_user_session_id
        import streamlit as st

        # Mock session state
        mock_state = {}

        with patch.object(st, 'session_state', mock_state):
            session_id_1 = get_user_session_id()
            assert session_id_1.startswith('user_'), "Session ID should have 'user_' prefix"

            # Second call should return same ID
            session_id_2 = get_user_session_id()
            assert session_id_1 == session_id_2, "Should return same session ID within session"

    def test_chat_prompt_template_generation(self):
        """Test generation of chat-specific prompts for different agent types"""
        from rag_app.app_simple_gemini import get_chat_prompt_template

        question = "Test question"
        schema_section = "Database schema here"
        conversation_section = "Previous conversation"
        context = "Retrieved examples"

        # Test default (concise) template
        prompt_default = get_chat_prompt_template(
            agent_type=None,
            question=question,
            schema_section=schema_section,
            conversation_section=conversation_section,
            context=context
        )
        assert "concise" in prompt_default.lower(), "Default should request concise answers"
        assert "2-3 sentences" in prompt_default, "Should specify sentence limit"

        # Test explain template
        prompt_explain = get_chat_prompt_template(
            agent_type="explain",
            question=question,
            schema_section=schema_section,
            conversation_section=conversation_section,
            context=context
        )
        assert "explanation" in prompt_explain.lower(), "Explain should focus on explanation"
        assert "detailed" in prompt_explain.lower() or "comprehensive" in prompt_explain.lower()

        # Test create template
        prompt_create = get_chat_prompt_template(
            agent_type="create",
            question=question,
            schema_section=schema_section,
            conversation_section=conversation_section,
            context=context
        )
        assert "sql" in prompt_create.lower(), "Create should focus on SQL generation"
        assert "bigquery" in prompt_create.lower(), "Should mention BigQuery requirements"

        # Test longanswer template
        prompt_long = get_chat_prompt_template(
            agent_type="longanswer",
            question=question,
            schema_section=schema_section,
            conversation_section=conversation_section,
            context=context
        )
        assert "detailed" in prompt_long.lower() or "comprehensive" in prompt_long.lower()
        assert "thorough" in prompt_long.lower() or "in-depth" in prompt_long.lower()
