.PHONY: install dev test lint format

install:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

dev:
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

lint:
	ruff check .

format:
	ruff format .
	ruff check . --fix
