# AI-SOC

AI-SOC is a modular security operations backend that ingests telemetry, detects
threats, correlates incidents, scores anomalies, maps ATT&CK techniques, and runs
queued AI-assisted investigations.

## Scope

Implemented through Sprint 7:

- normalized event and bulk ingestion
- rule-based and Isolation Forest alert generation
- credential-compromise incident correlation and timelines
- MITRE ATT&CK technique catalog and rule mappings
- persisted LangGraph investigation workflow with structured LLM output
- Redis investigation queue and standalone worker
- PostgreSQL persistence, Alembic migrations, Docker Compose, and automated tests

Still deferred:

- Next.js frontend implementation
- authentication and authorization
- WebSocket streaming
- AWS deployment

## Repository Layout

```text
backend/     FastAPI application, tests, migrations, scripts
frontend/    Placeholder structure
infra/       Local container orchestration and nginx placeholder
ml/          ML support files
simulator/   Synthetic telemetry scenarios
docs/        Architecture and API notes
```

## Quick Start

1. Review `backend/.env.example`. AI investigation remains disabled until a
   provider and key are configured.
2. Start PostgreSQL, Redis, the API, and investigation worker:

   ```bash
   docker compose -f infra/docker-compose.yml up --build
   ```

3. Open `http://localhost:8000/api/v1/health` or `/docs`.

## Backend Commands

From the `backend/` directory:

```bash
pip install -e .[dev]
alembic upgrade head
pytest
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Notes

- Event ingestion remains synchronous and does not wait for LLM investigation.
- Investigation results are structured, evidence-linked, validated, and persisted.
- Telemetry supplied to the LLM is allowlisted, sanitized, and size-bounded.
