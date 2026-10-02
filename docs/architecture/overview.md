# Architecture Overview

AI-SOC is a modular monolith with a Next.js analyst console and a separate
asynchronous investigation process:

- Next.js provides memory-only browser authentication state, generated API
  types, protected layouts, role-aware navigation, and the SOC shell.
- FastAPI accepts events and exposes incident, MITRE, and investigation APIs.
- Human requests use short-lived bearer tokens backed by revocable rotating
  sessions; telemetry producers use separately scoped service API keys.
- PostgreSQL stores events, alerts, incidents, ML registry metadata, ATT&CK data,
  investigation jobs, sanitized context snapshots, and validated results.
- PostgreSQL also stores users, fixed roles, refresh-session hashes, service-key
  hashes, and append-only security audit records.
- Redis carries investigation job IDs and realtime Pub/Sub messages without
  becoming the source of truth.
- The worker atomically claims queued jobs and executes a typed LangGraph.
- The LLM provider boundary supports OpenAI Responses and Google AI Studio's
  OpenAI-compatible structured Chat Completions, and remains mockable for tests.
- Alembic for schema migrations
- Docker Compose for local development

Browser development permits credentials only from explicit `CORS_ORIGINS`. The
production proxy contract serves the frontend and `/api` from one HTTPS origin;
access tokens stay in browser memory and refresh tokens remain HttpOnly cookies.

Event detection and incident correlation remain synchronous for correctness, while
AI investigation is explicitly requested and asynchronous so provider latency or
failure cannot interrupt telemetry ingestion.

Realtime browser connections use short-lived, one-time Redis-backed tickets bound
to the authenticated session family. FastAPI publishes versioned event, alert,
incident, and investigation envelopes after successful database commits; the
Nginx gateway forwards `/api/v1/realtime` WebSocket upgrades.
