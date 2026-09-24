# AI-SOC

AI-SOC is a modular security operations backend that ingests telemetry, detects
threats, correlates incidents, scores anomalies, maps ATT&CK techniques, and runs
queued AI-assisted investigations.

## Scope

Implemented through Sprint 9:

- normalized event and bulk ingestion
- rule-based and Isolation Forest alert generation
- credential-compromise incident correlation and timelines
- MITRE ATT&CK technique catalog and rule mappings
- persisted LangGraph investigation workflow with structured LLM output
- Redis investigation queue and standalone worker
- rotating human authentication sessions, fixed RBAC, scoped ingestion keys,
  login throttling, and append-only audit history
- Next.js frontend foundation with secure session restoration, generated API
  types, role-aware navigation, and a responsive SOC application shell
- PostgreSQL persistence, Alembic migrations, Docker Compose, and automated tests

Still deferred:

- full event, alert, incident, MITRE, ML, and investigation screens
- WebSocket streaming
- AWS deployment

## Repository Layout

```text
backend/     FastAPI application, tests, migrations, scripts
frontend/    Next.js analyst console
infra/       Container orchestration and Nginx same-origin gateway
ml/          ML support files
simulator/   Synthetic telemetry scenarios
docs/        Architecture and API notes
```

## Quick Start

1. Create `backend/.env` from `backend/.env.example`, generate a unique
   `SECRET_KEY` with `openssl rand -hex 32`, and configure optional AI settings.
2. Start PostgreSQL, Redis, the API, and investigation worker:

   ```bash
   docker compose -f infra/docker-compose.yml up --build
   ```

3. Create the first administrator interactively:

   ```bash
   docker compose -f infra/docker-compose.yml exec backend \
     python scripts/create_admin.py --email admin@example.com --full-name "SOC Admin"
   ```

4. Open the same-origin analyst console at `http://localhost:8080`, the direct
   Next.js development server at `http://localhost:3000`, or the API
   documentation at `http://localhost:8000/docs`.

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
- Human API access uses bearer tokens; event ingestion uses an `events:write`
  service key. See `docs/api/authentication.md`.
