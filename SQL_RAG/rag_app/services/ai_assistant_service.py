#!/usr/bin/env python3
"""
AI Assistant Service for SQL Playground

Provides AI-powered SQL assistance using Google Gemini:
- SQL Explanation: Generate human-readable explanations
- SQL Completion: Autocomplete suggestions
- SQL Fix: Debug and fix broken queries
"""

import json
import logging
from typing import List, Dict, Optional

from gemini_client import GeminiClient
from schema_manager import SchemaManager
from llm_registry import get_llm_registry
from prompt_templates.sql_assistant import (
    get_explain_prompt,
    get_complete_prompt,
    get_fix_prompt
)

logger = logging.getLogger(__name__)


class AIAssistantService:
    """AI-powered SQL assistance using Gemini"""

    def __init__(self, gemini_client: GeminiClient, schema_manager: SchemaManager):
        """
        Initialize AI Assistant Service.

        Args:
            gemini_client: Configured GeminiClient instance
            schema_manager: SchemaManager for database schema access
        """
        self.gemini = gemini_client
        self.schema = schema_manager
        logger.info("✅ AI Assistant Service initialized")

    def explain_sql(self, sql: str, schema_context: Optional[str] = None) -> str:
        """
        Generate human-readable explanation of SQL query.

        Args:
            sql: SQL query to explain
            schema_context: Optional pre-generated schema context. If None, will be extracted.

        Returns:
            Human-readable explanation text

        Raises:
            Exception: If explanation generation fails
        """
        try:
            logger.info(f"🤖 Generating explanation for SQL query ({len(sql)} chars)")

            # Get schema context if not provided
            if schema_context is None:
                table_names = self.schema.extract_tables_from_content(sql)
                schema_context = self.schema.get_relevant_schema(
                    table_names,
                    max_tables=10,
                    include_bigquery_guidance=True
                )
                logger.info(f"📊 Extracted {len(table_names)} tables for context: {table_names}")

            # Generate prompt
            prompt = get_explain_prompt(sql, schema_context)

            # Call Gemini
            explanation = self.gemini.invoke(prompt)

            if explanation and len(explanation.strip()) > 50:
                logger.info(f"✅ Explanation generated ({len(explanation)} chars)")
                return explanation.strip()
            else:
                logger.warning("⚠️ Explanation too short or empty")
                return "Unable to generate a detailed explanation. The query structure may be too complex or unclear."

        except Exception as e:
            logger.error(f"❌ Error generating explanation: {str(e)}")
            raise

    def complete_sql(
        self,
        partial_sql: str,
        cursor_position: Dict[str, int],
        schema_context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Suggest SQL completions based on partial query.

        Args:
            partial_sql: Incomplete SQL query (text before cursor)
            cursor_position: Cursor location {"line": int, "column": int}
            schema_context: Optional pre-generated schema context. If None, uses all tables.

        Returns:
            List of suggestions: [{"completion": "...", "explanation": "..."}, ...]

        Raises:
            Exception: If completion generation fails
        """
        try:
            logger.info(f"🤖 Generating completions for partial SQL ({len(partial_sql)} chars)")

            # Get schema context if not provided - use all tables for autocomplete
            if schema_context is None:
                all_tables = self.schema.get_all_tables()
                # Limit to first 20 tables to avoid token limits
                schema_context = self.schema.get_relevant_schema(
                    all_tables[:20],
                    max_tables=20,
                    include_bigquery_guidance=False
                )
                logger.info(f"📊 Using schema context with {min(20, len(all_tables))} tables")

            # Generate prompt
            prompt = get_complete_prompt(partial_sql, cursor_position, schema_context)

            # Call Gemini
            response_text = self.gemini.invoke(prompt)

            # Parse JSON response
            try:
                # Clean up response - remove markdown code blocks if present
                cleaned_response = response_text.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()

                result = json.loads(cleaned_response)
                suggestions = result.get("suggestions", [])

                if suggestions and len(suggestions) > 0:
                    logger.info(f"✅ Generated {len(suggestions)} completions")
                    return suggestions
                else:
                    logger.warning("⚠️ No suggestions in response")
                    return self._get_fallback_completions(partial_sql)

            except json.JSONDecodeError as je:
                logger.error(f"❌ JSON parsing failed: {str(je)}")
                logger.error(f"Response text: {response_text[:200]}...")
                return self._get_fallback_completions(partial_sql)

        except Exception as e:
            logger.error(f"❌ Error generating completions: {str(e)}")
            # Return fallback suggestions instead of raising
            return self._get_fallback_completions(partial_sql)

    def fix_sql(
        self,
        broken_sql: str,
        error_message: str,
        schema_context: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Debug and fix broken SQL query.

        Args:
            broken_sql: SQL query that failed
            error_message: Error message from BigQuery
            schema_context: Optional pre-generated schema context. If None, will be extracted.

        Returns:
            Dict with keys: "diagnosis", "fixed_sql", "changes"

        Raises:
            Exception: If fix generation fails
        """
        try:
            logger.info(f"🤖 Analyzing broken SQL ({len(broken_sql)} chars)")
            logger.info(f"Error: {error_message[:100]}...")

            # Get schema context if not provided
            if schema_context is None:
                table_names = self.schema.extract_tables_from_content(broken_sql)
                schema_context = self.schema.get_relevant_schema(
                    table_names,
                    max_tables=10,
                    include_bigquery_guidance=True
                )
                logger.info(f"📊 Extracted {len(table_names)} tables for context: {table_names}")

            # Generate prompt
            prompt = get_fix_prompt(broken_sql, error_message, schema_context)

            # Call Gemini
            response_text = self.gemini.invoke(prompt)

            # Parse JSON response
            try:
                # Clean up response - remove markdown code blocks if present
                cleaned_response = response_text.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()

                result = json.loads(cleaned_response)

                # Validate required fields
                required_fields = ["diagnosis", "fixed_sql", "changes"]
                if all(field in result for field in required_fields):
                    logger.info("✅ SQL fix generated successfully")
                    return {
                        "diagnosis": result["diagnosis"],
                        "fixed_sql": result["fixed_sql"],
                        "changes": result["changes"]
                    }
                else:
                    missing = [f for f in required_fields if f not in result]
                    logger.error(f"❌ Missing required fields in response: {missing}")
                    raise ValueError(f"Incomplete fix response: missing {missing}")

            except json.JSONDecodeError as je:
                logger.error(f"❌ JSON parsing failed: {str(je)}")
                logger.error(f"Response text: {response_text[:200]}...")
                raise ValueError(f"Failed to parse fix response: {str(je)}")

        except Exception as e:
            logger.error(f"❌ Error fixing SQL: {str(e)}")
            raise

    def _get_fallback_completions(self, partial_sql: str) -> List[Dict[str, str]]:
        """
        Provide fallback keyword completions when AI fails.

        Args:
            partial_sql: Partial SQL query

        Returns:
            List of basic keyword suggestions
        """
        logger.info("Using fallback keyword completions")

        partial_upper = partial_sql.upper().strip()

        # Simple keyword-based suggestions
        if "SELECT" not in partial_upper:
            return [
                {"completion": "SELECT", "explanation": "Start a SELECT query"},
                {"completion": "WITH", "explanation": "Start a CTE (Common Table Expression)"}
            ]
        elif "FROM" not in partial_upper and "SELECT" in partial_upper:
            return [
                {"completion": "FROM", "explanation": "Specify the source table"},
                {"completion": "* FROM", "explanation": "Select all columns from table"}
            ]
        elif "WHERE" not in partial_upper and "FROM" in partial_upper:
            return [
                {"completion": "WHERE", "explanation": "Add filter conditions"},
                {"completion": "GROUP BY", "explanation": "Group results by columns"},
                {"completion": "ORDER BY", "explanation": "Sort results"}
            ]
        else:
            return [
                {"completion": "LIMIT", "explanation": "Limit number of results"},
                {"completion": "ORDER BY", "explanation": "Sort results"},
                {"completion": "GROUP BY", "explanation": "Group results by columns"}
            ]


# Global instance for singleton pattern
_ai_assistant_service: Optional[AIAssistantService] = None


def get_ai_assistant_service() -> AIAssistantService:
    """
    Get global AI assistant service instance (singleton pattern).

    Returns:
        Configured AIAssistantService instance

    Raises:
        Exception: If service initialization fails
    """
    global _ai_assistant_service

    if _ai_assistant_service is None:
        try:
            # Get LLM client from registry (uses generator model - gemini-2.5-pro by default)
            registry = get_llm_registry()
            gemini_client = registry.get_generator()

            # Get schema manager
            # Import here to avoid circular imports
            from data.app_data_loader import load_schema_manager
            schema_manager = load_schema_manager()

            # Create service
            _ai_assistant_service = AIAssistantService(gemini_client, schema_manager)
            logger.info("✅ AI Assistant Service singleton initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize AI Assistant Service: {str(e)}")
            raise

    return _ai_assistant_service
