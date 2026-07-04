.PHONY: lint format check clean test test-mock-server setup-venv install-hooks

# Python files
PYTHON_FILES := $(shell find custom_components -name "*.py")

# Default target
all: lint

# Enable the repo's git hooks (pre-commit runs `make check`).
install-hooks:
	@git config core.hooksPath .githooks
	@echo "Git hooks enabled (core.hooksPath = .githooks)."
	@echo "Commits now run 'make check' first."

# Note: If you're using a virtual environment, activate it before running these commands
# Example: source venv/bin/activate

# Setup virtual environment
setup-venv:
	python -m venv .venv
	pip install -r requirements.txt
	@echo "Virtual environment created at .venv/"
	@echo "To activate, run: source .venv/bin/activate"

# Run all linters
lint: ruff

# Run ruff linter
ruff:
	python -m ruff check custom_components

# Format code with black and isort
format:
	python -m isort custom_components
	python -m black custom_components

# Check formatting without making changes
check:
	python -m isort --check-only custom_components
	python -m black --check custom_components

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
