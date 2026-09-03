# ==========================================================
# Firmware Regression Intelligence (FRI)
#
# Development Makefile
# ==========================================================

PYTHON := python3
PIP := pip

PACKAGE := fri

.DEFAULT_GOAL := help

# ----------------------------------------------------------
# Configurable Parameters
# ----------------------------------------------------------

REPO ?= .
GOOD ?= HEAD~20
BAD ?= HEAD
FAILURE ?= boot

# ----------------------------------------------------------
# Help
# ----------------------------------------------------------

.PHONY: help

help:
	@echo ""
	@echo "Firmware Regression Intelligence (FRI)"
	@echo ""
	@echo "Usage:"
	@echo "  make install"
	@echo "  make dev"
	@echo "  make format"
	@echo "  make lint"
	@echo "  make test"
	@echo "  make coverage"
	@echo "  make run REPO=<repo> GOOD=<sha> BAD=<sha> FAILURE=<type>"
	@echo "  make html REPO=<repo> GOOD=<sha> BAD=<sha> FAILURE=<type>"
	@echo "  make json REPO=<repo> GOOD=<sha> BAD=<sha> FAILURE=<type>"
	@echo "  make build"
	@echo "  make clean"
	@echo ""

# ----------------------------------------------------------
# Installation
# ----------------------------------------------------------

.PHONY: install

install:
	$(PIP) install -e .

.PHONY: dev

dev:
	$(PIP) install -e ".[dev]"

# ----------------------------------------------------------
# Formatting
# ----------------------------------------------------------

.PHONY: format

format:
	black fri tests
	ruff check --fix fri tests

# ----------------------------------------------------------
# Static Analysis
# ----------------------------------------------------------

.PHONY: lint

lint:
	ruff check fri
	mypy fri

# ----------------------------------------------------------
# Unit Tests
# ----------------------------------------------------------

.PHONY: test

test:
	pytest

# ----------------------------------------------------------
# Coverage
# ----------------------------------------------------------

.PHONY: coverage

coverage:
	pytest --cov=fri --cov-report=term-missing

# ----------------------------------------------------------
# Run Investigation
# ----------------------------------------------------------

.PHONY: run

run:
	fri investigate \
		--repo $(REPO) \
		--good $(GOOD) \
		--bad $(BAD) \
		--failure $(FAILURE)

# ----------------------------------------------------------
# HTML Report
# ----------------------------------------------------------

.PHONY: html

html:
	fri investigate \
		--repo $(REPO) \
		--good $(GOOD) \
		--bad $(BAD) \
		--failure $(FAILURE) \
		--html

# ----------------------------------------------------------
# JSON Report
# ----------------------------------------------------------

.PHONY: json

json:
	fri investigate \
		--repo $(REPO) \
		--good $(GOOD) \
		--bad $(BAD) \
		--failure $(FAILURE) \
		--json

# ----------------------------------------------------------
# Build Package
# ----------------------------------------------------------

.PHONY: build

build:
	$(PYTHON) -m build

# ----------------------------------------------------------
# Project Tree
# ----------------------------------------------------------

.PHONY: tree

tree:
	tree -L 3

# ----------------------------------------------------------
# Clean
# ----------------------------------------------------------

.PHONY: clean

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info

# ----------------------------------------------------------
# Full Validation
# ----------------------------------------------------------

.PHONY: ci

ci: format lint test

	@echo ""
	@echo "========================================="
	@echo "FRI validation completed successfully."
	@echo "========================================="