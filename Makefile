.PHONY: install format lint test fixture dbt-build dashboard compose-up

install:
	python -m pip install -e ".[dev,quality,analytics]"

format:
	isort .
	black .
	ruff check . --fix

lint:
	ruff check .
	black --check .
	isort --check-only .
	mypy src

test:
	coverage run -m pytest
	coverage report --fail-under=80

fixture:
	python scripts/create_ci_fixture.py data/ci

dbt-build:
	mct --data-root data/ci dbt-build --static-run data/ci/silver/static/20260101T120000000000Z

dashboard:
	streamlit run dashboard/app.py

compose-up:
	docker compose up --build -d

