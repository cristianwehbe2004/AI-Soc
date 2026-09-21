# Architecture Overview

AI-SOC is a modular monolith with a separate asynchronous investigation process:

- FastAPI accepts events and exposes incident, MITRE, and investigation APIs.
- Human requests use short-lived bearer tokens backed by revocable rotating
  sessions; telemetry producers use separately scoped service API keys.
- PostgreSQL stores events, alerts, incidents, ML registry metadata, ATT&CK data,
  investigation jobs, sanitized context snapshots, and validated results.
- PostgreSQL also stores users, fixed roles, refresh-session hashes, service-key
  hashes, and append-only security audit records.
- Redis carries investigation job IDs without becoming the source of truth.
- The worker atomically claims queued jobs and executes a typed LangGraph.
- The LLM provider boundary currently supports OpenAI Responses structured output
  and remains mockable for tests.
- Alembic for schema migrations
- Docker Compose for local development

Browser development permits credentials only from explicit `CORS_ORIGINS`. The
future production proxy will serve the frontend and `/api` from one HTTPS origin;
access tokens stay in browser memory and refresh tokens remain HttpOnly cookies.

Event detection and incident correlation remain synchronous for correctness, while
AI investigation is explicitly requested and asynchronous so provider latency or
failure cannot interrupt telemetry ingestion.
