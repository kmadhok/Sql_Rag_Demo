#!/usr/bin/env python3
"""
End-to-End Tests for Agent Workflows

Tests specialized agent functionality:
- @explain agent - detailed explanations
- @create agent - SQL generation
- @schema agent - LookML exploration
- @longanswer agent - comprehensive responses
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "rag_app"))


@pytest.mark.e2e
@pytest.mark.agent
class TestAgentWorkflows:
    """Test suite for specialized agent workflows"""

    def test_explain_agent_detection_and_usage(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test @explain agent for detailed explanations"""
        from rag_app.app_simple_gemini import (
            detect_chat_agent_type,
            answer_question_chat_mode
        )

        # Detect agent
        agent_type, question = detect_chat_agent_type("@explain How do joins work?")

        assert agent_type == "explain", "Should detect @explain agent"
        assert question == "How do joins work?", "Should extract question"

        # Use explain agent
        result = answer_question_chat_mode(
            question=question,
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type=agent_type
        )

        assert result is not None, "Explain agent should generate response"
        answer, sources, token_usage = result
        assert token_usage['agent_type'] == "explain", "Should track agent type"

    def test_create_agent_for_sql_generation(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test @create agent for SQL generation"""
        from rag_app.app_simple_gemini import (
            detect_chat_agent_type,
            answer_question_chat_mode
        )

        # Detect agent
        agent_type, question = detect_chat_agent_type("@create a query for user orders")

        assert agent_type == "create", "Should detect @create agent"
        assert question == "a query for user orders", "Should extract question"

        # Use create agent
        result = answer_question_chat_mode(
            question=question,
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type=agent_type
        )

        assert result is not None, "Create agent should generate response"
        answer, sources, token_usage = result
        assert token_usage['agent_type'] == "create", "Should track agent type"

    def test_longanswer_agent_for_detailed_responses(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test @longanswer agent for comprehensive responses"""
        from rag_app.app_simple_gemini import (
            detect_chat_agent_type,
            answer_question_chat_mode
        )

        # Detect agent
        agent_type, question = detect_chat_agent_type(
            "@longanswer Tell me everything about database indexing"
        )

        assert agent_type == "longanswer", "Should detect @longanswer agent"
        assert question == "Tell me everything about database indexing", "Should extract question"

        # Use longanswer agent
        result = answer_question_chat_mode(
            question=question,
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type=agent_type
        )

        assert result is not None, "Longanswer agent should generate response"
        answer, sources, token_usage = result
        assert token_usage['agent_type'] == "longanswer", "Should track agent type"

    def test_schema_agent_overview_query(self, mock_lookml_safe_join_map):
        """Test @schema agent with overview query"""
        from rag_app.app_simple_gemini import handle_schema_query

        # Empty question for overview
        response = handle_schema_query("", mock_lookml_safe_join_map)

        assert "Overview" in response or "overview" in response, "Should provide overview"
        assert "Explores" in response or "explores" in response, "Should mention explores"

    def test_schema_agent_join_query(self, mock_lookml_safe_join_map):
        """Test @schema agent with join-related query"""
        from rag_app.app_simple_gemini import handle_schema_query

        response = handle_schema_query(
            "how do I join users with orders",
            mock_lookml_safe_join_map
        )

        assert "join" in response.lower(), "Should discuss joins"
        # Should provide join information
        assert len(response) > 50, "Should provide detailed response"

    def test_schema_agent_explore_query(self, mock_lookml_safe_join_map):
        """Test @schema agent with explore listing query"""
        from rag_app.app_simple_gemini import handle_schema_query

        response = handle_schema_query(
            "show me all explores",
            mock_lookml_safe_join_map
        )

        assert "explore" in response.lower(), "Should discuss explores"
        assert "users" in response.lower(), "Should mention users explore"

    def test_schema_agent_table_specific_query(self, mock_lookml_safe_join_map):
        """Test @schema agent with table-specific query"""
        from rag_app.app_simple_gemini import handle_schema_query

        response = handle_schema_query(
            "tell me about the users table",
            mock_lookml_safe_join_map
        )

        assert "users" in response.lower(), "Should mention users table"

    def test_schema_agent_without_lookml_data(self):
        """Test @schema agent when LookML data is not available"""
        from rag_app.app_simple_gemini import handle_schema_query

        response = handle_schema_query("show explores", None)

        assert "not available" in response.lower(), "Should indicate data not available"

    def test_schema_agent_unrecognized_query(self, mock_lookml_safe_join_map):
        """Test @schema agent with unrecognized query"""
        from rag_app.app_simple_gemini import handle_schema_query

        response = handle_schema_query(
            "some random unrelated query",
            mock_lookml_safe_join_map
        )

        # Should provide helpful guidance
        assert "can help" in response.lower() or "try" in response.lower(), \
            "Should provide helpful response"

    def test_agent_indicator_display(self):
        """Test agent indicator strings for UI"""
        from rag_app.app_simple_gemini import get_chat_agent_indicator

        assert "Explain" in get_chat_agent_indicator("explain"), "Should have explain indicator"
        assert "Create" in get_chat_agent_indicator("create"), "Should have create indicator"
        assert "Schema" in get_chat_agent_indicator("schema"), "Should have schema indicator"
        assert "Detailed" in get_chat_agent_indicator("longanswer"), \
            "Should have longanswer indicator"
        assert "Concise" in get_chat_agent_indicator(None), "Should have default indicator"

    def test_explain_agent_prompt_template(self):
        """Test that @explain agent uses detailed explanation template"""
        from rag_app.app_simple_gemini import get_chat_prompt_template

        prompt = get_chat_prompt_template(
            agent_type="explain",
            question="How do joins work?",
            schema_section="Schema here",
            conversation_section="",
            context="Context here"
        )

        assert "explanation" in prompt.lower(), "Should focus on explanation"
        assert "detailed" in prompt.lower() or "comprehensive" in prompt.lower(), \
            "Should request detailed response"

    def test_create_agent_prompt_template(self):
        """Test that @create agent uses SQL generation template"""
        from rag_app.app_simple_gemini import get_chat_prompt_template

        prompt = get_chat_prompt_template(
            agent_type="create",
            question="Create a query for users",
            schema_section="Schema here",
            conversation_section="",
            context="Context here"
        )

        assert "sql" in prompt.lower(), "Should focus on SQL"
        assert "generate" in prompt.lower() or "create" in prompt.lower(), \
            "Should request generation"
        assert "bigquery" in prompt.lower(), "Should mention BigQuery"

    def test_longanswer_agent_prompt_template(self):
        """Test that @longanswer agent uses comprehensive template"""
        from rag_app.app_simple_gemini import get_chat_prompt_template

        prompt = get_chat_prompt_template(
            agent_type="longanswer",
            question="Explain indexing",
            schema_section="Schema here",
            conversation_section="",
            context="Context here"
        )

        assert "detailed" in prompt.lower() or "comprehensive" in prompt.lower(), \
            "Should request detailed response"
        assert "thorough" in prompt.lower() or "in-depth" in prompt.lower(), \
            "Should request thorough coverage"

    def test_default_agent_concise_template(self):
        """Test that default (no agent) uses concise template"""
        from rag_app.app_simple_gemini import get_chat_prompt_template

        prompt = get_chat_prompt_template(
            agent_type=None,
            question="Show users",
            schema_section="Schema here",
            conversation_section="",
            context="Context here"
        )

        assert "concise" in prompt.lower(), "Should request concise response"
        assert "2-3 sentences" in prompt, "Should specify sentence limit"

    def test_agent_with_conversation_context(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test agent usage with conversation history"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        conversation_context = """User: What are joins?
Assistant: Joins combine data from multiple tables based on related columns.
"""

        result = answer_question_chat_mode(
            question="Give me an example",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context=conversation_context,
            agent_type="explain"
        )

        assert result is not None, "Should handle conversation context with agent"

    def test_agent_with_schema_injection(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test agent with schema injection enabled"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        result = answer_question_chat_mode(
            question="Create a query for users table",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type="create"
        )

        assert result is not None, "Should use schema with create agent"
        answer, sources, token_usage = result

        # Verify schema was used
        if 'schema_filtering' in token_usage:
            assert token_usage['schema_filtering']['enabled'], "Schema should be enabled"

    def test_multiple_agents_in_sequence(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test using different agents in sequence"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        # First use explain agent
        result1 = answer_question_chat_mode(
            question="How do joins work?",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type="explain"
        )
        assert result1 is not None, "Explain agent should work"

        # Then use create agent
        result2 = answer_question_chat_mode(
            question="Create a join query",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type="create"
        )
        assert result2 is not None, "Create agent should work"

        # Then use default
        result3 = answer_question_chat_mode(
            question="Is this correct?",
            vector_store=mock_vector_store,
            k=10,
            schema_manager=mock_schema_manager,
            conversation_context="",
            agent_type=None
        )
        assert result3 is not None, "Default agent should work"

    def test_schema_agent_direct_response(self, mock_lookml_safe_join_map):
        """Test that @schema agent returns direct response without using LLM"""
        from rag_app.app_simple_gemini import handle_schema_query

        # Schema agent should not require vector store or LLM
        response = handle_schema_query("", mock_lookml_safe_join_map)

        # Response should be immediate and structured
        assert isinstance(response, str), "Should return string response"
        assert len(response) > 0, "Should have content"

    def test_agent_type_persistence_in_token_usage(
        self,
        mock_vector_store,
        mock_gemini_client,
        mock_schema_manager
    ):
        """Test that agent type is tracked in token usage"""
        from rag_app.app_simple_gemini import answer_question_chat_mode

        for agent in ["explain", "create", "longanswer", None]:
            result = answer_question_chat_mode(
                question="Test question",
                vector_store=mock_vector_store,
                k=5,
                schema_manager=mock_schema_manager,
                conversation_context="",
                agent_type=agent
            )

            if result:
                answer, sources, token_usage = result
                assert token_usage['agent_type'] == agent, \
                    f"Should track agent type: {agent}"

    def test_edge_case_agent_keyword_variations(self):
        """Test edge cases in agent keyword detection"""
        from rag_app.app_simple_gemini import detect_chat_agent_type

        # Extra spaces
        agent_type, question = detect_chat_agent_type("@explain   Multiple  spaces")
        assert agent_type == "explain", "Should handle extra spaces"

        # No space after keyword
        agent_type, question = detect_chat_agent_type("@createquery")
        assert agent_type == "create", "Should handle no space"
        assert question == "query", "Should extract remaining text"

        # Lowercase variations are not detected (case-sensitive)
        agent_type, question = detect_chat_agent_type("@EXPLAIN uppercase")
        assert agent_type is None, "Keywords should be case-sensitive"
