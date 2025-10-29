# Makefile for SQL Service Testing
.PHONY: help test test-sql test-all test-coverage install-test-deps clean

help:
	@echo "Available targets:"
	@echo "  test-sql     - Run SQL service tests"
	@echo "  test-all     - Run all tests"
	@echo "  test-coverage- Run tests with coverage report"
	@echo "  install-test-deps - Install test dependencies"
	@echo "  clean       - Clean test files"
	@echo ""
	@echo "Examples:"
	@echo "  make test-sql"
	@echo "  make test-coverage"

install-test-deps:
	@echo "Installing test dependencies..."
	pip install pytest pytest-asyncio pytest-cov pytest-mock httpx

test:
	@echo "Running all tests..."
	pytest tests/ -v

test-sql:
	@echo "Running SQL service tests..."
	pytest tests/test_sql_service.py -v

test-all:
	@echo "Running all tests..."
	pytest tests/ -v

test-coverage:
	@echo "Running tests with coverage report..."
	pytest tests/ -cov=services --cov=api --cov-report=html --cov-report=term-missing

test-integration:
	@echo "Running integration tests..."
	pytest tests/ -m integration -v

test-unit:
	@echo "Running unit tests..."
	pytest tests/ -m unit -v

clean:
	@echo "Cleaning up test files..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf tests/__pycache__
	find tests/ -name '*.pyc' -delete 2>/dev/null || true