.PHONY: install install-dev verify lint format typecheck test test-cov docker-build docker-up docker-down clean dashboard

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

verify:
	python scripts/verify_environment.py

dashboard:
	streamlit run src/autoclean/presentation/streamlit_app.py

lint:
	ruff check src tests

format:
	black src tests
	ruff check --fix src tests

typecheck:
	mypy src

test:
	pytest -m unit

test-cov:
	pytest --cov --cov-report=term-missing

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
