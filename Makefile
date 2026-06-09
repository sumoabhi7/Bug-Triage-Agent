.PHONY: install lint format test db-up db-down

install:
	uv sync

lint:
	ruff check .

format:
	ruff format .

test:
	pytest

db-up:
	docker compose up -d

db-down:
	docker compose down