# AI Investigation API

Sprint 7 runs investigation outside event ingestion. PostgreSQL stores job state
and results, Redis carries investigation IDs, and the worker executes the typed
LangGraph workflow.

Configure `LLM_ENABLED=true`, `LLM_PROVIDER=google`, `LLM_API_KEY`,
`LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`, and
`LLM_MODEL=gemini-3.5-flash-lite` before submitting jobs. The Google AI Studio key
must be stored in the ignored local `backend/.env` file, never committed.

Automatic investigations are disabled by default. To enable them, set
`AUTOMATIC_INVESTIGATIONS_ENABLED=true` and choose a minimum severity with
`AUTOMATIC_INVESTIGATION_MIN_SEVERITY`. The dispatcher applies a per-incident
Redis cooldown from `AUTOMATIC_INVESTIGATION_COOLDOWN_SECONDS` and preserves the
existing investigation idempotency and evidence-validation boundaries.

## Request an investigation

`POST /api/v1/incidents/{incident_id}/investigations`

Returns `202 Accepted` with a persisted `queued` job. Repeating the request for
an unchanged incident and prompt version returns the same job instead of creating
duplicate provider calls.

## Read investigation status and result

`GET /api/v1/investigations/{investigation_id}`

The status is one of `queued`, `running`, `completed`, or `failed`. A completed
job includes evidence findings, risk analysis, ATT&CK context, an investigation
narrative, recommendations, provider response IDs, and token usage.

## List incident investigations

`GET /api/v1/incidents/{incident_id}/investigations`

Results are ordered newest first. Updating an incident changes its context hash,
allowing a new investigation while preserving earlier results.

Telemetry is treated as untrusted input. The workflow excludes raw payloads,
size-bounds context, requires structured provider output, and rejects citations
that do not reference loaded alerts, events, or MITRE techniques.
