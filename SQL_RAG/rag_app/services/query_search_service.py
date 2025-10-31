#!/usr/bin/env python3
"""
Service helpers for the Simple Query Search pipeline.

This module encapsulates the logic that was previously embedded directly
inside the Streamlit UI so it can be imported from tests or other entry
points (FastAPI/CLI) without depending on Streamlit state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from simple_rag_simple_gemini import answer_question_simple_gemini
from services.sql_extraction_service import extract_sql_from_text

try:
    from core.sql_validator import ValidationLevel
except ImportError:  # pragma: no cover - optional dependency
    ValidationLevel = None  # type: ignore

try:
    from hybrid_retriever import SearchWeights
except ImportError:  # pragma: no cover - optional dependency
    SearchWeights = Any  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class QuerySearchSettings:
    """Configuration knobs for the Query Search pipeline."""

    k: int = 20
    gemini_mode: bool = False
    hybrid_search: bool = False
    search_weights: Optional[SearchWeights] = None
    auto_adjust_weights: bool = True
    query_rewriting: bool = False
    sql_validation: bool = False
    validation_level: Optional[Any] = None
    excluded_tables: Optional[List[str]] = None
    user_context: str = ""
    conversation_context: str = ""
    agent_type: Optional[str] = None
    llm_model: Optional[str] = None


@dataclass
class QuerySearchResult:
    """Structured output returned by ``run_query_search``."""

    question: str
    answer_text: Optional[str] = None
    sql: Optional[str] = None
    sources: List[Document] = field(default_factory=list)
    usage: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def succeeded(self) -> bool:
        return self.error is None and self.answer_text is not None


def run_query_search(
    question: str,
    *,
    vector_store: FAISS,
    schema_manager: Any = None,
    lookml_safe_join_map: Any = None,
    settings: Optional[QuerySearchSettings] = None,
    sql_extractor: Optional[Callable[[str], Optional[str]]] = None,
) -> QuerySearchResult:
    """
    Execute the Simple Query Search pipeline without Streamlit dependencies.

    Args:
        question: User natural-language question.
        vector_store: Preloaded FAISS vector store.
        schema_manager: Optional schema manager instance for schema injection.
        lookml_safe_join_map: Optional LookML join hints.
        settings: Pipeline settings (defaults mirror Streamlit's Simple mode).
        sql_extractor: Optional custom SQL extractor; defaults to service helper.

    Returns:
        ``QuerySearchResult`` containing the answer, SQL (if extracted),
        supporting documents, token usage metadata, or an error message.
    """

    settings = settings or QuerySearchSettings()
    question_stripped = (question or "").strip()

    if not question_stripped:
        return QuerySearchResult(question=question or "", error="Question is empty.")

    if vector_store is None:
        return QuerySearchResult(question=question_stripped, error="Vector store is not available.")

    # Prepare kwargs for the RAG function, preserving the existing defaults.
    rag_kwargs: Dict[str, Any] = dict(
        question=question_stripped,
        vector_store=vector_store,
        k=settings.k,
        gemini_mode=settings.gemini_mode,
        hybrid_search=settings.hybrid_search,
        search_weights=settings.search_weights,
        auto_adjust_weights=settings.auto_adjust_weights,
        query_rewriting=settings.query_rewriting,
        schema_manager=schema_manager,
        lookml_safe_join_map=lookml_safe_join_map,
        conversation_context=settings.conversation_context,
        agent_type=settings.agent_type,
        sql_validation=settings.sql_validation,
        excluded_tables=settings.excluded_tables,
        user_context=settings.user_context,
        llm_model=settings.llm_model,
    )

    if settings.sql_validation:
        # Only supply validation level if the enum is available; fall back to default otherwise.
        if settings.validation_level is not None:
            rag_kwargs["validation_level"] = settings.validation_level
        elif ValidationLevel is not None:
            rag_kwargs["validation_level"] = ValidationLevel.SCHEMA_STRICT

    try:
        rag_result = answer_question_simple_gemini(**rag_kwargs)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Query search pipeline failed: %s", exc)
        return QuerySearchResult(question=question_stripped, error=str(exc))

    if not rag_result:
        return QuerySearchResult(question=question_stripped, error="RAG pipeline returned no result.")

    answer_text, sources, usage = rag_result

    sql_text: Optional[str] = None
    extractor = sql_extractor or extract_sql_from_text
    if answer_text and extractor:
        try:
            sql_text = extractor(answer_text)
        except Exception as exc:  # pragma: no cover - extractor failures should not crash pipeline
            logger.warning("SQL extraction failed: %s", exc)
            sql_text = None

    return QuerySearchResult(
        question=question_stripped,
        answer_text=answer_text,
        sql=sql_text,
        sources=list(sources or []),
        usage=dict(usage or {}),
        error=None,
    )


__all__ = [
    "QuerySearchSettings",
    "QuerySearchResult",
    "run_query_search",
]
