.PHONY: install dev lint format typecheck test test-cov build run clean

install:
	pip install .

dev:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/ --strict

test:
	pytest -v

test-cov:
	pytest --cov=src --cov-report=term-missing --cov-fail-under=80

build:
	docker build -t discord-media-bot .

run:
	docker compose up -d

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache .ruff_cache htmlcov .coverage
