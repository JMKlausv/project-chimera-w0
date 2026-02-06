.PHONY: help install test test-unit test-skills test-all lint format clean \
       docker-build docker-run docker-test run

# Project config
PROJECT_NAME := chymera-w0
DOCKER_IMAGE := $(PROJECT_NAME):latest
PYTHON := uv run python
PYTEST := uv run pytest

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────

install: ## Install dependencies with uv
	uv sync

# ──────────────────────────────────────────────
# Testing
# ──────────────────────────────────────────────

test: test-unit ## Run default tests (unit)

test-unit: ## Run unit tests
	$(PYTEST) tests/unit/ -v

test-models: ## Run model/schema tests only
	$(PYTEST) tests/unit/models/ -v

test-skills: ## Run skill contract tests only
	$(PYTEST) tests/unit/skills/ -v

test-all: ## Run all tests with coverage
	$(PYTEST) tests/ -v --tb=short

# ──────────────────────────────────────────────
# Code Quality
# ──────────────────────────────────────────────

lint: ## Run linter (ruff)
	uv run ruff check src/ tests/

format: ## Auto-format code (ruff)
	uv run ruff format src/ tests/

# ──────────────────────────────────────────────
# Docker
# ──────────────────────────────────────────────

docker-build: ## Build Docker image
	docker build -t $(DOCKER_IMAGE) -f dockerfile .

docker-run: ## Run app in Docker
	docker run --rm $(DOCKER_IMAGE)

docker-test: docker-build ## Build and run tests in Docker
	docker run --rm $(DOCKER_IMAGE)

# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────

run: ## Run the application
	$(PYTHON) main.py

# ──────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	rm -rf .pytest_cache __pycache__ .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
