# Makefile for Repository Analysis System
# Provides convenient commands for development, testing, and deployment

.PHONY: help install test test-unit test-integration test-e2e test-live test-all lint format clean docker-build docker-up docker-down

# Default target
help:
	@echo "Repository Analysis System - Make Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install all dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all unit and integration tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-e2e         Run end-to-end tests"
	@echo "  make test-live        Run live API tests (requires GITHUB_TOKEN)"
	@echo "  make test-all         Run all tests including live tests"
	@echo "  make coverage         Generate test coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linters (flake8, black, isort)"
	@echo "  make format           Auto-format code with black and isort"
	@echo "  make type-check       Run mypy type checking"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker images"
	@echo "  make docker-up        Start services with Docker Compose"
	@echo "  make docker-down      Stop services"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove temporary files and caches"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-asyncio pytest-mock
	pip install flake8 black isort mypy
	pip install safety bandit

# Testing
test:
	pytest tests/ -m "not live and not slow" -v

test-unit:
	pytest tests/ -m "unit" -v

test-integration:
	pytest tests/ -m "integration and not live" -v

test-e2e:
	pytest tests/ -m "e2e and not live" -v

test-live:
	@if [ -z "$$GITHUB_TOKEN" ]; then \
		echo "Error: GITHUB_TOKEN environment variable not set"; \
		exit 1; \
	fi
	pytest tests/ -m "live" -v

test-all:
	pytest tests/ -v

coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

# Code Quality
lint:
	flake8 src tests --max-line-length=120 --exclude=__pycache__,venv
	black --check src tests
	isort --check-only src tests

format:
	black src tests
	isort src tests

type-check:
	mypy src --ignore-missing-imports

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Database
db-setup:
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "Using local PostgreSQL..."; \
		psql -U postgres -d repo_analysis -f src/storage/schema.sql; \
	else \
		echo "Using DATABASE_URL..."; \
		psql $$DATABASE_URL -f src/storage/schema.sql; \
	fi

db-reset:
	@echo "WARNING: This will drop and recreate the database!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		dropdb repo_analysis; \
		createdb repo_analysis; \
		make db-setup; \
	fi

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type f -name '.coverage' -delete
	rm -rf build/ dist/ *.egg-info/

# Development
run:
	python scripts/run_graph.py

run-sync:
	python -m src.sync.github_sync

run-baseline:
	python -m src.baseline.initializer

# Health Checks
health-check:
	@echo "Running health checks..."
	@python -c "from src.sync.github_sync import GitHubSyncService; from src.utils.config import load_config; config = load_config(); service = GitHubSyncService(config); print(service.health_check())"
