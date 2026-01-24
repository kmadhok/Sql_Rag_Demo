#!/usr/bin/env python3
"""
True Integration Tests for Complete SQL RAG Pipeline

These tests validate the ENTIRE pipeline end-to-end with NO MOCKS:
1. Load real vector store created from sample CSV
2. Ask predefined test questions
3. Retrieve similar queries using real embeddings
4. Generate SQL with real Gemini API
5. Validate SQL syntax
6. Execute SQL against real BigQuery (read-only)
7. Validate results

Unlike the unit tests in tests/e2e/, these integration tests:
- Use REAL OpenAI embeddings (not mocked)
- Use REAL FAISS vector stores (not mocked)
- Use REAL Gemini API (not mocked)
- Use REAL BigQuery execution (not mocked)
- Validate the COMPLETE user experience

Requirements:
- OPENAI_API_KEY environment variable
- GEMINI_API_KEY environment variable
- BigQuery credentials (GOOGLE_APPLICATION_CREDENTIALS or gcloud auth)
- Test vector store created by setup_test_vector_store.py
"""

import pytest
import re
import time
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "rag_app"))

# Import real components (not mocks!)
from app_simple_gemini import answer_question_chat_mode
from core.bigquery_executor import BigQueryExecutor, extract_sql_from_text


@pytest.mark.integration
class TestCompleteRAGPipeline:
    """
    Integration tests for the complete RAG pipeline

    Each test:
    1. Takes a predefined question
    2. Runs it through the real RAG pipeline
    3. Validates the generated SQL
    4. Executes against BigQuery (if safe)
    5. Validates the results
    """

    def test_simple_product_query(
        self,
        vector_store,
        schema_manager,
        bigquery_client,
        test_results_logger
    ):
        """Test simple SELECT query for expensive products"""
        question = "Show me the 10 most expensive products"

        test_results_logger.info(f"Testing question: {question}")
        start_time = time.time()

        # Run through the complete RAG pipeline
        result = answer_question_chat_mode(
            question=question,
            vector_store=vector_store,
            k=10,
            schema_manager=schema_manager,
            conversation_context="",
            agent_type=None
        )

        assert result is not None, "RAG pipeline should return a result"
        answer, source_docs, token_usage = result

        elapsed = time.time() - start_time
        test_results_logger.info(f"Pipeline completed in {elapsed:.2f}s")
        test_results_logger.info(f"Answer: {answer[:200]}...")
        test_results_logger.info(f"Retrieved {len(source_docs)} source documents")
        test_results_logger.info(f"Token usage: {token_usage}")

        # Validate answer is not empty
        assert answer, "Answer should not be empty"
        assert len(source_docs) > 0, "Should retrieve at least one source document"

        # Extract SQL from answer
        sql = extract_sql_from_text(answer)

        if sql:
            test_results_logger.info(f"Generated SQL: {sql}")

            # Validate SQL patterns
            assert "SELECT" in sql.upper(), "SQL should contain SELECT"
            assert "products" in sql.lower(), "SQL should reference products table"
            assert "retail_price" in sql.lower() or "price" in sql.lower(), "SQL should reference price"
            assert "LIMIT" in sql.upper(), "SQL should have a LIMIT clause"

            # Execute against BigQuery
            executor = BigQueryExecutor(bigquery_client)
            query_result = executor.execute_query(sql, dry_run_first=True)

            assert query_result.success, f"Query execution failed: {query_result.error}"
            assert query_result.df is not None, "Query should return results"
            assert len(query_result.df) > 0, "Query should return at least one row"

            test_results_logger.info(f"Query executed successfully, returned {len(query_result.df)} rows")

    def test_aggregation_user_count(
        self,
        vector_store,
        schema_manager,
        bigquery_client,
        test_results_logger
    ):
        """Test COUNT aggregation query"""
        question = "How many users are there for each gender?"

        test_results_logger.info(f"Testing question: {question}")

        result = answer_question_chat_mode(
            question=question,
            vector_store=vector_store,
            k=10,
            schema_manager=schema_manager,
            conversation_context="",
            agent_type=None
        )

        assert result is not None, "RAG pipeline should return a result"
        answer, source_docs, token_usage = result

        test_results_logger.info(f"Answer: {answer[:200]}...")

        # Extract and validate SQL
        sql = extract_sql_from_text(answer)

        if sql:
            test_results_logger.info(f"Generated SQL: {sql}")

            assert "COUNT" in sql.upper(), "SQL should contain COUNT"
            assert "GROUP BY" in sql.upper(), "SQL should contain GROUP BY"
            assert "gender" in sql.lower(), "SQL should reference gender column"
            assert "users" in sql.lower(), "SQL should reference users table"

            # Execute query
            executor = BigQueryExecutor(bigquery_client)
            query_result = executor.execute_query(sql, dry_run_first=True)

            assert query_result.success, f"Query failed: {query_result.error}"
            assert query_result.df is not None
            assert len(query_result.df) > 0

            test_results_logger.info(f"Query executed successfully: {len(query_result.df)} rows")

    def test_join_users_orders(
        self,
        vector_store,
        schema_manager,
        bigquery_client,
        test_results_logger
    ):
        """Test JOIN query between users and orders"""
        question = "Show me all orders with user information"

        test_results_logger.info(f"Testing question: {question}")

        result = answer_question_chat_mode(
            question=question,
            vector_store=vector_store,
            k=10,
            schema_manager=schema_manager,
            conversation_context="",
            agent_type=None
        )

        assert result is not None, "RAG pipeline should return a result"
        answer, source_docs, token_usage = result

        test_results_logger.info(f"Answer: {answer[:200]}...")

        # Extract and validate SQL
        sql = extract_sql_from_text(answer)

        if sql:
            test_results_logger.info(f"Generated SQL: {sql}")

            assert "JOIN" in sql.upper(), "SQL should contain JOIN"
            assert "users" in sql.lower(), "SQL should reference users table"
            assert "orders" in sql.lower(), "SQL should reference orders table"

            # Execute query (with LIMIT to avoid large results)
            # Add LIMIT if not present
            if "LIMIT" not in sql.upper():
                sql = sql.rstrip(';') + " LIMIT 100"

            executor = BigQueryExecutor(bigquery_client)
            query_result = executor.execute_query(sql, dry_run_first=True)

            assert query_result.success, f"Query failed: {query_result.error}"
            test_results_logger.info(f"JOIN query executed successfully")

    @pytest.mark.parametrize("test_case_id", [
        "simple_select_products",
        "aggregation_count_by_gender",
        "aggregation_avg_age_by_state",
        "join_users_orders"
    ])
    def test_from_yaml(
        self,
        test_case_id,
        test_questions,
        vector_store,
        schema_manager,
        bigquery_client,
        test_results_logger
    ):
        """Parameterized test that runs all test cases from YAML file"""
        # Find test case in YAML
        test_case = None
        for tc in test_questions:
            if tc.get("id") == test_case_id:
                test_case = tc
                break

        if not test_case:
            pytest.skip(f"Test case {test_case_id} not found in YAML")

        question = test_case["question"]
        description = test_case.get("description", "")
        expected_patterns = test_case.get("expected_sql_patterns", [])
        should_execute = test_case.get("should_execute", False)
        agent_type = test_case.get("agent_type")

        test_results_logger.info(f"Test: {test_case_id}")
        test_results_logger.info(f"Description: {description}")
        test_results_logger.info(f"Question: {question}")

        # Run through RAG pipeline
        start_time = time.time()
        result = answer_question_chat_mode(
            question=question,
            vector_store=vector_store,
            k=10,
            schema_manager=schema_manager,
            conversation_context="",
            agent_type=agent_type
        )
        elapsed = time.time() - start_time

        assert result is not None, "RAG pipeline should return a result"
        answer, source_docs, token_usage = result

        test_results_logger.info(f"Completed in {elapsed:.2f}s")
        test_results_logger.info(f"Answer length: {len(answer)} chars")
        test_results_logger.info(f"Source docs: {len(source_docs)}")

        # Validate answer
        assert answer, "Answer should not be empty"

        # Extract SQL if expected
        sql = extract_sql_from_text(answer)

        if expected_patterns:
            assert sql, f"Expected SQL but none found in answer"

            test_results_logger.info(f"Generated SQL: {sql}")

            # Validate SQL patterns
            for pattern in expected_patterns:
                assert pattern.upper() in sql.upper(), f"SQL missing expected pattern: {pattern}"

            # Execute if safe
            if should_execute:
                # Add safety LIMIT if not present
                if "LIMIT" not in sql.upper():
                    sql = sql.rstrip(';') + " LIMIT 100"

                executor = BigQueryExecutor(bigquery_client)
                query_result = executor.execute_query(sql, dry_run_first=True)

                if query_result.success:
                    test_results_logger.info(f"✅ Query executed successfully")
                    if query_result.df is not None:
                        test_results_logger.info(f"   Returned {len(query_result.df)} rows")
                else:
                    test_results_logger.error(f"❌ Query execution failed: {query_result.error}")
                    pytest.fail(f"Query execution failed: {query_result.error}")

    def test_agent_explain(
        self,
        vector_store,
        schema_manager,
        test_results_logger
    ):
        """Test @explain agent workflow"""
        question = "@explain What is the schema of the products table?"

        test_results_logger.info(f"Testing question: {question}")

        result = answer_question_chat_mode(
            question=question,
            vector_store=vector_store,
            k=10,
            schema_manager=schema_manager,
            conversation_context="",
            agent_type="explain"
        )

        assert result is not None, "RAG pipeline should return a result"
        answer, source_docs, token_usage = result

        test_results_logger.info(f"Answer: {answer[:500]}...")

        # @explain should provide schema information, not SQL
        assert "product" in answer.lower(), "Answer should mention products"
        # Should NOT generate executable SQL
        sql = extract_sql_from_text(answer)
        if sql:
            test_results_logger.warning(f"@explain generated SQL (unexpected): {sql}")

    def test_agent_create(
        self,
        vector_store,
        schema_manager,
        bigquery_client,
        test_results_logger
    ):
        """Test @create agent workflow"""
        question = "@create Find the top 5 customers by total order value"

        test_results_logger.info(f"Testing question: {question}")

        result = answer_question_chat_mode(
            question=question,
            vector_store=vector_store,
            k=10,
            schema_manager=schema_manager,
            conversation_context="",
            agent_type="create"
        )

        assert result is not None, "RAG pipeline should return a result"
        answer, source_docs, token_usage = result

        test_results_logger.info(f"Answer: {answer[:500]}...")

        # @create should generate SQL
        sql = extract_sql_from_text(answer)
        assert sql, "@create should generate SQL"

        test_results_logger.info(f"Generated SQL: {sql}")

        # Validate SQL complexity (should have aggregation)
        assert "SUM" in sql.upper() or "COUNT" in sql.upper(), "Should have aggregation"
        assert "GROUP BY" in sql.upper(), "Should have GROUP BY"
        assert "LIMIT" in sql.upper() or "TOP" in sql.upper(), "Should limit results"

    def test_vector_retrieval_quality(
        self,
        vector_store,
        test_results_logger
    ):
        """Test that vector retrieval returns relevant similar queries"""
        question = "Show me the most expensive products"

        test_results_logger.info(f"Testing vector retrieval for: {question}")

        # Retrieve similar documents
        docs = vector_store.similarity_search_with_score(question, k=5)

        assert len(docs) > 0, "Should retrieve at least one document"

        for i, (doc, score) in enumerate(docs):
            test_results_logger.info(f"Doc {i+1} (score: {score:.3f}): {doc.page_content[:100]}...")

        # First result should be highly relevant (low distance score)
        top_doc, top_score = docs[0]
        assert top_score < 0.5, f"Top result should be relevant (score < 0.5), got {top_score}"

        # Top result should mention products or related terms
        content = top_doc.page_content.lower()
        assert "product" in content or "retail" in content or "price" in content, \
            "Top result should be related to products"

    def test_sql_safety_validation(
        self,
        vector_store,
        schema_manager,
        test_results_logger
    ):
        """Test that SQL safety validation blocks dangerous queries"""
        dangerous_questions = [
            "DELETE all products",
            "DROP TABLE users",
            "UPDATE orders SET status = 'cancelled'"
        ]

        for question in dangerous_questions:
            test_results_logger.info(f"Testing safety for: {question}")

            result = answer_question_chat_mode(
                question=question,
                vector_store=vector_store,
                k=10,
                schema_manager=schema_manager,
                conversation_context="",
                agent_type=None
            )

            if result:
                answer, source_docs, token_usage = result
                sql = extract_sql_from_text(answer)

                if sql:
                    test_results_logger.warning(f"Generated SQL: {sql}")
                    # Should NOT contain dangerous keywords
                    dangerous_keywords = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
                    for keyword in dangerous_keywords:
                        assert keyword not in sql.upper(), \
                            f"Generated SQL should not contain {keyword}"

    def test_conversation_context(
        self,
        vector_store,
        schema_manager,
        test_results_logger
    ):
        """Test that conversation context is maintained across queries"""
        # First question
        question1 = "Show me the products table"
        result1 = answer_question_chat_mode(
            question=question1,
            vector_store=vector_store,
            k=10,
            schema_manager=schema_manager,
            conversation_context="",
            agent_type=None
        )

        assert result1 is not None
        answer1, _, _ = result1

        test_results_logger.info(f"Q1: {question1}")
        test_results_logger.info(f"A1: {answer1[:200]}...")

        # Second question with context
        question2 = "Now filter for items over $100"
        conversation_context = f"User: {question1}\nAssistant: {answer1}\n"

        result2 = answer_question_chat_mode(
            question=question2,
            vector_store=vector_store,
            k=10,
            schema_manager=schema_manager,
            conversation_context=conversation_context,
            agent_type=None
        )

        assert result2 is not None
        answer2, _, _ = result2

        test_results_logger.info(f"Q2: {question2}")
        test_results_logger.info(f"A2: {answer2[:200]}...")

        # Second answer should reference products and price filtering
        sql2 = extract_sql_from_text(answer2)
        if sql2:
            assert "products" in sql2.lower(), "Should still reference products table"
            assert "WHERE" in sql2.upper() or ">" in sql2, "Should have filter condition"
