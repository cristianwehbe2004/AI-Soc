# AI-SOC

Sprint 1 sets up the repository and backend foundation for an AI-powered Security Operations Center without implementing telemetry ingestion, alerts, incidents, ML, LangGraph, LLM integrations, MITRE mapping, frontend application code, authentication, WebSockets, or deployment automation.

## Scope

Implemented in this sprint:

- repository structure
- FastAPI backend foundation
- environment-based configuration
- PostgreSQL and Redis connectivity
- structured JSON logging
- health endpoint
- Alembic wiring
- Docker Compose local stack
- basic automated tests

Intentionally deferred:

- events, alerts, incidents
- detection and correlation logic
- machine learning pipelines and models
- AI investigation workflows
- Next.js frontend implementation
- authentication and authorization
- WebSocket streaming
- AWS deployment

## Repository Layout

```text
backend/     FastAPI application, tests, migrations, scripts
frontend/    Placeholder structure only for now
infra/       Local container orchestration and nginx placeholder
ml/          Placeholder structure for future ML work
simulator/   Placeholder structure for future synthetic telemetry
docs/        Architecture and API notes
```

## Quick Start

1. Copy `backend/.env.example` to `backend/.env`.
2. Start the local stack:

   ```bash
   docker compose -f infra/docker-compose.yml up --build
   ```

3. Open `http://localhost:8000/api/v1/health`.

## Backend Commands

From the `backend/` directory:

```bash
pip install -e .[dev]
alembic upgrade head
pytest
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Notes

- The backend is designed as a modular monolith.
- The health endpoint validates both PostgreSQL and Redis connectivity.
- Frontend, ML, simulator, and worker directories are scaffolded only to support future sprints.
