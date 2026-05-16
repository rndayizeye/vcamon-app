.PHONY: run build test lint

run:
	docker compose up

build:
	docker compose build

test:
	pytest tests/ -v

lint:
	python3 -m ruff check app/

shell:
	docker compose exec app bash