.PHONY: help install install-dev clean test test-cov lint format type-check build release shell

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $1, $2}'

install:  ## Install the package and dependencies
	poetry install --no-dev

install-dev:  ## Install the package with dev dependencies
	poetry install

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test:  ## Run tests
	poetry run pytest tests/

test-cov:  ## Run tests with coverage
	poetry run pytest tests/ --cov=zephflow --cov-report=html --cov-report=term-missing

lint:  ## Run linting
	poetry run flake8 zephflow/

format:  ## Format code with black and isort
	poetry run black zephflow/ tests/
	poetry run isort zephflow/ tests/

format-check:  ## Check code formatting
	poetry run black --check zephflow/ tests/
	poetry run isort --check zephflow/ tests/

type-check:  ## Run type checking with mypy
	poetry run mypy zephflow/

check: format-check lint type-check test  ## Run all checks

build:  ## Build the package
	poetry build

release:  ## Create a release (requires version parameter)
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make release VERSION=0.2.1"; \
		exit 1; \
	fi
	python scripts/release.py --version $(VERSION)

shell:  ## Open a poetry shell
	poetry shell

update-deps:  ## Update dependencies
	poetry update

show-deps:  ## Show dependency tree
	poetry show --tree

clear-cache:  ## Clear the JAR cache
	poetry run python -c "from zephflow import JarManager; JarManager().clear_cache()"

run-example:  ## Run the quickstart example
	poetry run python examples/quickstart.py

version:  ## Show current version
	@echo "Poetry version: $$(poetry version --short)"
	@echo "Dynamic version: $$(poetry run python -c 'from poetry_dynamic_versioning import get_version; print(get_version("."))')"