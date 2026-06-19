.PHONY: install up down logs run worker test lint fmt typecheck migrate revision

install:
	pip install -e ".[dev]"

up:           ## Start the full stack (api, worker, db, redis)
	docker compose up --build

down:         ## Stop the stack and drop volumes
	docker compose down -v

logs:
	docker compose logs -f

run:          ## Run the API locally (needs local Postgres/Redis or use `make up`)
	uvicorn app.main:app --reload

worker:       ## Run a Celery worker locally (use --pool=solo on Windows)
	celery -A app.celery_app.celery_app worker --loglevel=info

test:
	pytest -q

lint:
	ruff check .

fmt:
	ruff format .

typecheck:
	mypy app

migrate:      ## Apply migrations
	alembic upgrade head

revision:     ## Autogenerate a migration: make revision m="add leads"
	alembic revision --autogenerate -m "$(m)"
