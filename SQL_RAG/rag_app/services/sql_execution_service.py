#!/usr/bin/env python3
"""
Service layer for executing generated SQL against BigQuery.

This module lifts the non-UI logic from ``app_simple_gemini.py`` so the same
execution pipeline can be reused by Streamlit, FastAPI, or CLI entry points.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

try:
    import pandas as pd
except ImportError:  # pragma: no cover - pandas is a hard dependency for execution results
    pd = None  # type: ignore

from core.bigquery_executor import BigQueryExecutor, QueryResult

logger = logging.getLogger(__name__)


@dataclass
class SQLExecutionSettings:
    """Configuration for SQL execution."""

    project_id: Optional[str] = None
    dataset_id: Optional[str] = None
    dry_run: bool = False
    max_bytes_billed: int = 100_000_000
    debug_mode: bool = False


@dataclass
class SQLExecutionResponse:
    """Structured response returned after attempting to execute SQL."""

    success: bool
    sql: str
    result: Optional[QueryResult] = None
    error_message: Optional[str] = None
    validation_message: Optional[str] = None
    initialized: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


def _resolve_project_dataset(settings: SQLExecutionSettings) -> SQLExecutionSettings:
    """Fill in project/dataset defaults from environment variables."""
    project = settings.project_id or os.getenv("BIGQUERY_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise EnvironmentError(
            "BigQuery project not configured. Set BIGQUERY_PROJECT_ID or GOOGLE_CLOUD_PROJECT."
        )

    dataset = settings.dataset_id or os.getenv("BIGQUERY_DATASET")
    if not dataset:
        default_dataset_project = os.getenv("SCHEMA_EXPORT_PROJECT", "bigquery-public-data")
        default_dataset_name = os.getenv("SCHEMA_EXPORT_DATASET", "thelook_ecommerce")
        dataset = f"{default_dataset_project}.{default_dataset_name}"

    settings.project_id = project
    settings.dataset_id = dataset
    return settings


def initialize_executor(settings: SQLExecutionSettings) -> BigQueryExecutor:
    """
    Create a ``BigQueryExecutor`` using the provided settings.

    Raises:
        Exception if initialization fails (callers should catch and surface).
    """
    settings = _resolve_project_dataset(settings)
    logger.info(
        "Initializing BigQueryExecutor (project=%s, dataset=%s)",
        settings.project_id,
        settings.dataset_id,
    )
    executor = BigQueryExecutor(
        project_id=settings.project_id,
        dataset_id=settings.dataset_id,
    )
    return executor


def validate_sql_safety(
    sql: str,
    executor: Optional[BigQueryExecutor] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate SQL using available safety mechanisms.

    Returns:
        Tuple of (is_valid, validation_message).
    """
    sql_text = (sql or "").strip()
    if not sql_text:
        return False, "SQL is empty."

    try:
        from security.sql_validator import validate_sql_legacy_wrapper

        return validate_sql_legacy_wrapper(sql_text)
    except ImportError:
        logger.debug("security.sql_validator not available; using executor validation fallback.")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Security validator error: %s", exc)

    if executor and hasattr(executor, "validate_sql_safety"):
        try:
            return executor.validate_sql_safety(sql_text)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Executor validation failed: %s", exc)

    # If no validator is available, default to allowing execution (legacy behavior).
    return True, None


def run_sql_execution(
    sql: str,
    *,
    executor: Optional[BigQueryExecutor] = None,
    settings: Optional[SQLExecutionSettings] = None,
) -> SQLExecutionResponse:
    """
    Execute SQL using BigQuery with safety validation and detailed metadata.

    Args:
        sql: The SQL statement to run.
        executor: Optional pre-initialized executor; if not provided one will be created.
        settings: Execution settings (project, dataset, dry run, etc.).

    Returns:
        ``SQLExecutionResponse`` summarizing success, QueryResult, and any errors.
    """
    settings = settings or SQLExecutionSettings()
    sql_text = (sql or "").strip()

    if not sql_text:
        return SQLExecutionResponse(success=False, sql=sql or "", error_message="SQL is empty.")

    # Ensure executor availability.
    initialized = False
    local_executor = executor
    if local_executor is None:
        try:
            local_executor = initialize_executor(settings)
            initialized = True
        except Exception as exc:
            logger.error("Failed to initialize BigQuery executor: %s", exc)
            return SQLExecutionResponse(
                success=False,
                sql=sql_text,
                error_message=f"Failed to initialize BigQuery executor: {exc}",
            )

    # Safety validation
    is_valid, validation_message = validate_sql_safety(sql_text, executor=local_executor)
    if not is_valid:
        return SQLExecutionResponse(
            success=False,
            sql=sql_text,
            error_message=f"Safety validation failed: {validation_message}",
            validation_message=validation_message,
            initialized=initialized,
        )

    # Execute query.
    try:
        result = local_executor.execute_query(
            sql_text,
            dry_run=settings.dry_run,
            max_bytes_billed=settings.max_bytes_billed,
        )
        metadata = {
            "project_id": local_executor.project_id,
            "dataset_id": local_executor.dataset_id,
            "dry_run": settings.dry_run,
            "max_bytes_billed": settings.max_bytes_billed,
            "debug_mode": settings.debug_mode,
        }
        return SQLExecutionResponse(
            success=result.success,
            sql=sql_text,
            result=result,
            initialized=initialized,
            metadata=metadata,
        )
    except Exception as exc:
        logger.exception("SQL execution failed: %s", exc)
        return SQLExecutionResponse(
            success=False,
            sql=sql_text,
            error_message=str(exc),
            initialized=initialized,
        )


__all__ = [
    "SQLExecutionSettings",
    "SQLExecutionResponse",
    "run_sql_execution",
    "initialize_executor",
    "validate_sql_safety",
]
