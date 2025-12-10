#
# Makefile for Portuguese Parliament API project
#
#
# Frederico Muñoz <fsmunoz@gmail.com>
#

.PHONY: help test test-unit test-integration test-property test-contract test-coverage test-quick test-all test-parallel test-endpoint test-clean install dev-install run etl-fetch etl-transform etl-all clean lint format

# Default target
.DEFAULT_GOAL := help

# Help
# (Needs to be kept updated)
# ==============================================================================

help:
	@echo "=========================================================================="
	@echo " Portuguese Parliament API - Make Targets"
	@echo "=========================================================================="
	@echo ""
	@echo "Testing:"
	@echo "  make test              - Run standard test suite (unit + integration + contract)"
	@echo "  make test-quick        - Fast "smoke test" (unit + health check)"
	@echo "  make test-all          - Full test suite (including property-based tests)"
	@echo "  make test-unit         - Unit tests only"
	@echo "  make test-integration  - Integration tests only"
	@echo "  make test-property     - Property-based tests only (Hypothesis)"
	@echo "  make test-contract     - OpenAPI contract tests only"
	@echo "  make test-coverage     - Generate HTML coverage report"
	@echo "  make test-parallel     - Run tests in parallel (faster)"
	@echo "  make test-endpoint     - Test specific endpoint (e.g., ENDPOINT=votacoes)"
	@echo "  make test-clean        - Clean test artifacts"
	@echo ""
	@echo "Development:"
	@echo "  make install           - Install dependencies"
	@echo "  make dev-install       - Install dev dependencies"
	@echo "  make run               - Run API server locally"
	@echo "  make lint              - Lint code with ruff"
	@echo "  make format            - Format code with ruff"
	@echo ""
	@echo "ETL Pipeline:"
	@echo "  make etl-fetch         - Fetch JSON from parlamento.pt"
	@echo "  make etl-transform     - Transform JSON to Parquet"
	@echo "  make etl-all           - Run full ETL pipeline"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean             - Clean all artifacts"
	@echo ""
	@echo "=========================================================================="

# ==============================================================================
# Testing targets
# ==============================================================================

# We always source .venv/bin/activate
# We us https://docs.pytest.org/en/stable/ as the testing framework

# Quick smoke test (unit + basic integration)
test-quick:
	@echo "==> Running quick tests..."
	. .venv/bin/activate && pytest tests/test_api.py::test_health_check -v --tb=short

# Unit tests only (fast)
test-unit:
	@echo "==> Running unit tests..."
	. .venv/bin/activate && pytest tests/unit/ -v --tb=short -m unit

# Integration tests (endpoint tests)
test-integration:
	@echo "==> Running integration tests..."
	. .venv/bin/activate && pytest tests/integration/ tests/test_api.py -v --tb=short -m "not slow"

# Property-based tests (comprehensive, but slower)
test-property:
	@echo "==> Running property-based tests..."
	. .venv/bin/activate && pytest tests/property/ -v --tb=short -m property

# OpenAPI contract tests
test-contract:
	@echo "==> Running contract tests..."
	. .venv/bin/activate && pytest tests/contract/ -v --tb=short -m contract

# All tests (default, excludes property tests for speed)
test:
	@echo "==> Running all tests (excluding property)..."
	. .venv/bin/activate && pytest tests/test_api.py tests/test_regressions.py -v --tb=short

# Full test suite (includes property tests)
test-all:
	@echo "==> Running FULL test suite..."
	. .venv/bin/activate && pytest tests/ -v --tb=short

# Coverage report
test-coverage:
	@echo "==> Running tests with coverage..."
	. .venv/bin/activate && pytest tests/ --cov=app --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "==> Coverage report: htmlcov/index.html"
	@echo ""

# Parallel execution (fastest, perhaps it should be the default?)
test-parallel:
	@echo "==> Running tests in parallel..."
	. .venv/bin/activate && pytest tests/ -n auto -v --tb=short

# Specific endpoint (example: make test-endpoint ENDPOINT=votacoes)
test-endpoint:
ifndef ENDPOINT
	@echo "ERROR: Please specify ENDPOINT variable"
	@echo "Example: make test-endpoint ENDPOINT=votacoes"
	@exit 1
endif
	@echo "==> Running tests for $(ENDPOINT)..."
	. .venv/bin/activate && pytest tests/integration/test_$(ENDPOINT).py tests/test_api.py -k $(ENDPOINT) -v --tb=short

# Clean test artifacts
test-clean:
	@echo "==> Cleaning test artifacts..."
	rm -rf .pytest_cache htmlcov .coverage .hypothesis
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "==> Test artifacts cleaned"


# Development targets
# ==============================================================================
# We use pip; perhaps we should consider uv in the near future...

install:
	@echo "==> Installing dependencies..."
	. .venv/bin/activate && pip install -e .

dev-install:
	@echo "==> Installing dev dependencies..."
	. .venv/bin/activate && pip install -e ".[dev]"

run:
	@echo "==> Starting API server..."
	. .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	@echo "==> Linting code..."
	. .venv/bin/activate && ruff check app/ etl/ tests/

format:
	@echo "==> Formatting code..."
	. .venv/bin/activate && ruff format app/ etl/ tests/


# ETL Pipeline targets
# ==============================================================================

etl-fetch:
	@echo "==> Fetching data from parlamento.pt..."
	. .venv/bin/activate && python -m etl

etl-transform:
	@echo "==> Transforming JSON to Parquet..."
	. .venv/bin/activate && python -m etl.transform

etl-all: etl-fetch etl-transform
	@echo "==> ETL pipeline complete"


# Cleanup targets
# ==============================================================================

clean: test-clean
	@echo "==> Cleaning all artifacts..."
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "==> All artifacts cleaned"
