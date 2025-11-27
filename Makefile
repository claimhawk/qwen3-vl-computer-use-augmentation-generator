# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

.PHONY: all check lint typecheck complexity format clean install dev test build docs

# Use venv Python if available, fallback to python3
PYTHON := $(shell test -x .venv/bin/python && echo .venv/bin/python || echo python3)
SRC_DIR := src/cudag
TEST_DIR := tests

# Default target
all: check

# Setup virtualenv and install dependencies
install:
	python3 -m venv .venv
	.venv/bin/pip install -e .

# Install dev dependencies
dev: install
	.venv/bin/pip install -e ".[dev]"
	.venv/bin/pip install radon types-PyYAML pdoc3

# Run all quality checks
check: lint typecheck complexity
	@echo "✓ All checks passed!"

# Linting with ruff
lint:
	@echo "Running ruff..."
	$(PYTHON) -m ruff check $(SRC_DIR)
	$(PYTHON) -m ruff format --check $(SRC_DIR)

# Type checking with mypy
typecheck:
	@echo "Running mypy..."
	$(PYTHON) -m mypy $(SRC_DIR) --strict

# Complexity analysis with radon
complexity:
	@echo "Running complexity analysis..."
	@echo "Cyclomatic complexity (max C acceptable):"
	$(PYTHON) -m radon cc $(SRC_DIR) -a -nc --total-average
	@echo ""
	@echo "Maintainability index:"
	$(PYTHON) -m radon mi $(SRC_DIR) -nc

# Auto-format code
format:
	@echo "Formatting code..."
	$(PYTHON) -m ruff format $(SRC_DIR)
	$(PYTHON) -m ruff check --fix $(SRC_DIR)

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Run tests (using PYTHONPATH to ensure local source is used)
test:
	PYTHONPATH=src $(PYTHON) -m pytest $(TEST_DIR) -v

# Build package
build: clean
	$(PYTHON) -m build

# Generate API documentation
docs:
	@echo "Generating documentation..."
	$(PYTHON) -m pdoc --html --output-dir docs $(SRC_DIR) --force
	@echo "Documentation generated in docs/"
