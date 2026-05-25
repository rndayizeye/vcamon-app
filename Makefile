MESSAGE ?= schema update

.PHONY: run build test lint run-api test-api db-upgrade db-revision

run:
	docker compose up

build:
	docker compose build

test:
	pytest tests/ -v

test-api:
	pytest tests/test_fastapi_cases.py -v

lint:
	python3 -m ruff check app/ fastapi_app/

run-api: db-upgrade
	uvicorn fastapi_app.main:app --reload

db-upgrade:
	python3 -m alembic -c fastapi_app/alembic.ini upgrade head

db-revision:
	python3 -m alembic -c fastapi_app/alembic.ini revision --autogenerate -m "$(MESSAGE)"

shell:
	docker compose exec app bash
