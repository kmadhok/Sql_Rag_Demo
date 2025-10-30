#!/usr/bin/env python3
"""
Unit tests for services.sql_execution_service run_sql_execution and helpers.
"""

from __future__ import annotations

import pytest

from core.bigquery_executor import QueryResult
from services.sql_execution_service import (
    SQLExecutionSettings,
    run_sql_execution,
    validate_sql_safety,
)


class FakeExecutor:
    def __init__(self, valid: bool = True, validation_message: str | None = None, result_success: bool = True):
        self.project_id = "test-project"
        self.dataset_id = "test-dataset"
        self.valid = valid
        self.validation_message = validation_message
        self.result_success = result_success
        self.executed = False
        self.execute_kwargs = {}
        self.validation_calls = 0

    def validate_sql_safety(self, sql: str):
        self.validation_calls += 1
        return self.valid, self.validation_message

    def execute_query(self, sql: str, dry_run: bool = False, max_bytes_billed: int = 100_000_000):
        self.executed = True
        self.execute_kwargs = {
            "sql": sql,
            "dry_run": dry_run,
            "max_bytes_billed": max_bytes_billed,
        }
        return QueryResult(success=self.result_success, total_rows=1)


def test_run_sql_execution_success(monkeypatch):
    """Successful execution returns QueryResult and metadata."""

    executor = FakeExecutor(valid=True, result_success=True)
    settings = SQLExecutionSettings(dry_run=True, max_bytes_billed=50_000_000)

    response = run_sql_execution(
        "SELECT 1",
        executor=executor,
        settings=settings,
    )

    assert response.success is True
    assert response.result is not None
    assert response.result.success is True
    assert executor.executed is True
    assert response.metadata["dry_run"] is True
    assert response.metadata["max_bytes_billed"] == 50_000_000


def test_run_sql_execution_validation_failure():
    """Validation failure should short-circuit execution and return an error."""

    executor = FakeExecutor(valid=False, validation_message="Write operations not allowed")
    response = run_sql_execution(
        "DELETE FROM table",
        executor=executor,
        settings=SQLExecutionSettings(),
    )

    assert response.success is False
    assert "Safety validation failed" in (response.error_message or "")
    assert response.validation_message is not None
    assert executor.executed is False


def test_run_sql_execution_initialization_error(monkeypatch):
    """Initialization errors are surfaced in the response."""

    def boom(_settings):
        raise RuntimeError("Initialization failed")

    monkeypatch.setattr("services.sql_execution_service.initialize_executor", boom)

    response = run_sql_execution("SELECT 1")

    assert response.success is False
    assert "Initialization failed" in (response.error_message or "")


def test_validate_sql_safety_falls_back_to_executor(monkeypatch):
    """validate_sql_safety should fallback to executor when validator errors."""

    executor = FakeExecutor(valid=True, validation_message=None)

    try:
        import security.sql_validator as sql_validator
    except ImportError:  # pragma: no cover - environment without security module
        sql_validator = None

    if sql_validator is not None:
        def boom(_sql: str):
            raise RuntimeError("validator boom")

        monkeypatch.setattr(sql_validator, "validate_sql_legacy_wrapper", boom)

    is_valid, message = validate_sql_safety("SELECT 1", executor=executor)

    assert is_valid is True
    assert message is None
    assert executor.validation_calls == 1
