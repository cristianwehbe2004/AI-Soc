COMPOSE_FILE=infra/docker-compose.yml

.PHONY: up down logs build test migrate

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

migrate:
	docker compose -f $(COMPOSE_FILE) run --rm backend alembic upgrade head
