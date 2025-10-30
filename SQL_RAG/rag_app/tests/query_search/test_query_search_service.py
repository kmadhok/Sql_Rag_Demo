#!/usr/bin/env python3
"""
Unit tests for services.query_search_service.run_query_search

These tests focus on the Simple Query Search flow in isolation so we can
refactor the Streamlit UI or add alternative entry-points (CLI/FastAPI)
with confidence. They rely on lightweight in-memory doubles for the FAISS
vector store, schema manager, and Gemini client.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import pytest
from langchain_core.documents import Document
from langchain_community.embeddings import FakeEmbeddings
from langchain_community.vectorstores import FAISS

import services.query_search_service as query_service


class DummySchemaManager:
    """Minimal schema manager double for testing."""

    def __init__(self) -> None:
        self.requests: Dict[str, Any] = {}

    def get_relevant_schema(self, tables):  # pragma: no cover - only called if schema injection enabled
        self.requests.setdefault("tables", []).append(tables)
        return "TABLE orders(order_id INT, total_amount FLOAT)"

    def get_table_info(self, table):  # pragma: no cover - not used in current tests
        return {"table": table}

    def get_table_columns(self, table):  # pragma: no cover - not used in current tests
        return ["column_a", "column_b"]


class StubGeminiClient:
    """
    Stand-in for GeminiClient that returns canned responses.

    It is injected via monkeypatching the registry lookup so
    ``answer_question_simple_gemini`` uses deterministic outputs.
    """

    def __init__(self, answer_text: str) -> None:
        self.answer_text = answer_text

    # The LangChain interface expects an ``invoke`` method.
    def invoke(self, *_args, **_kwargs):
        return self.answer_text


def _build_vector_store() -> FAISS:
    """Create a tiny FAISS index with predictable documents."""
    docs = [
        Document(page_content="orders table contains order_id and total_amount"),
        Document(page_content="users table has user_id, email, and city"),
    ]
    embeddings = FakeEmbeddings(size=8)
    return FAISS.from_documents(docs, embeddings)


@pytest.fixture(autouse=True)
def _clear_env():
    """Ensure test-specific env vars are removed."""
    original = os.environ.copy()
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


def test_run_query_search_success(monkeypatch):
    """run_query_search returns answer and SQL when Gemini outputs a code block."""

    vector_store = _build_vector_store()
    sql_answer = """Here is the query:

```sql
SELECT order_id, total_amount
FROM orders
WHERE total_amount > 100;
```
"""

    # Stub the Gemini registry used inside answer_question_simple_gemini
    class DummyRegistry:
        gen_model = "stub-model"

        def get_generator(self):
            return StubGeminiClient(sql_answer)

    monkeypatch.setattr("llm_registry.get_llm_registry", lambda: DummyRegistry())

    settings = query_service.QuerySearchSettings(k=2, sql_validation=False)
    result = query_service.run_query_search(
        "Show high-value orders",
        vector_store=vector_store,
        schema_manager=None,
        lookml_safe_join_map=None,
        settings=settings,
    )

    assert result.error is None
    assert result.answer_text and "Here is the query" in result.answer_text
    assert result.sql is not None
    assert "SELECT order_id" in result.sql
    assert result.sources is not None


def test_run_query_search_handles_empty_question():
    """Blank questions should produce a descriptive error."""

    vector_store = _build_vector_store()
    result = query_service.run_query_search(
        "   ",
        vector_store=vector_store,
        schema_manager=None,
        lookml_safe_join_map=None,
    )

    assert result.error == "Question is empty."
    assert result.answer_text is None
    assert result.sql is None


def test_run_query_search_handles_missing_vector_store():
    """If the vector store is not available we return an error."""

    settings = query_service.QuerySearchSettings()
    result = query_service.run_query_search(
        "What is the total revenue?",
        vector_store=None,  # type: ignore[arg-type]
        schema_manager=None,
        lookml_safe_join_map=None,
        settings=settings,
    )

    assert result.error == "Vector store is not available."
    assert result.answer_text is None
    assert result.sql is None
