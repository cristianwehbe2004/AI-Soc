COMPOSE_FILE=infra/docker-compose.yml

.PHONY: up down logs build test frontend-test frontend-build migrate ml-dataset ml-train ml-evaluate

up:
	docker compose -f $(COMPOSE_FILE) up --build

down:
	docker compose -f $(COMPOSE_FILE) down

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

build:
	docker compose -f $(COMPOSE_FILE) build

test:
	docker compose -f $(COMPOSE_FILE) run --rm backend pytest

frontend-test:
	docker compose -f $(COMPOSE_FILE) run --rm frontend npm run test:run

frontend-build:
	docker compose -f $(COMPOSE_FILE) run --rm frontend npm run build

migrate:
	docker compose -f $(COMPOSE_FILE) run --rm backend alembic upgrade head

ml-dataset:
	docker compose -f $(COMPOSE_FILE) run --rm backend python scripts/generate_ml_dataset.py

ml-train:
	docker compose -f $(COMPOSE_FILE) run --rm backend python scripts/train_isolation_forest.py artifacts/datasets/events_v1.csv

ml-evaluate:
	docker compose -f $(COMPOSE_FILE) run --rm backend python scripts/evaluate_isolation_forest.py
