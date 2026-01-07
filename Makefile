# Makefile for lib_zerodha development

.PHONY: help install install-dev test test-cov lint format clean build publish docs

# Default target
help:
	@echo "Available commands:"
	@echo "  install      Install package for production"
	@echo "  install-dev  Install package for development"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage"
	@echo "  lint         Run linting (ruff, mypy)"
	@echo "  format       Format code (black, isort)"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build package"
	@echo "  publish      Publish to PyPI"
	@echo "  docs         Generate documentation"

# Installation
install:
	uv sync --no-dev

install-dev:
	uv sync
	uv run pre-commit install

# Testing
test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ --cov=lib_zerodha --cov-report=html --cov-report=term

test-integration:
	uv run pytest tests/integration/ -v -m integration

# Code quality
lint:
	uv run ruff check lib_zerodha tests
	uv run mypy lib_zerodha

format:
	uv run black lib_zerodha tests examples
	uv run isort lib_zerodha tests examples
	uv run ruff format lib_zerodha tests examples

# Build and publish
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: clean
	uv build

publish: build
	uv publish

# Documentation
docs:
	uv run sphinx-build -b html docs/ docs/_build/

# Development
dev-server:
	uv run python -m lib_zerodha.examples.dev_server

check-all: lint test-cov
	@echo "All checks passed!"

# Performance testing
perf-test:
	uv run python -m pytest tests/performance/ -v