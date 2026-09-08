# Architecture Overview

AI-SOC is a modular monolith with a separate asynchronous investigation process:

- FastAPI accepts events and exposes incident, MITRE, and investigation APIs.
- PostgreSQL stores events, alerts, incidents, ML registry metadata, ATT&CK data,
  investigation jobs, sanitized context snapshots, and validated results.
- Redis carries investigation job IDs without becoming the source of truth.
- The worker atomically claims queued jobs and executes a typed LangGraph.
- The LLM provider boundary currently supports OpenAI Responses structured output
  and remains mockable for tests.
- Alembic for schema migrations
- Docker Compose for local development

Event detection and incident correlation remain synchronous for correctness, while
AI investigation is explicitly requested and asynchronous so provider latency or
failure cannot interrupt telemetry ingestion.
