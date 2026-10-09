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
an unchanged incident, attached evidence, and prompt version returns the same job
instead of creating duplicate provider calls.

## Attach incident evidence

`POST /api/v1/incidents/{incident_id}/evidence` requires incident-write permission.
`GET /api/v1/incidents/{incident_id}/evidence` requires SOC-read permission.
For example, an analyst can submit:

```json
{
  "kind": "network_observation",
  "source": "firewall log review",
  "summary": "Observed an allowed inbound connection to the restricted host",
  "network": {
    "source_zone": "internet",
    "destination_zone": "restricted",
    "destination_port": 3389,
    "protocol": "tcp",
    "disposition": "allowed"
  }
}
```

Other evidence kinds are `analyst_observation`, `asset_configuration`,
`identity_activity`, and `vulnerability_report`; they take `source`, `summary`,
and optional `observed_at`. Never submit secrets or raw private keys. Common
secret patterns are redacted before storage, but redaction is not a guarantee.
Adding evidence changes the investigation context hash; submit a new
investigation request to analyze it. Prior results remain available.

## Read investigation status and result

`GET /api/v1/investigations/{investigation_id}`

The status is one of `queued`, `running`, `completed`, or `failed`. A completed
job includes evidence findings, risk analysis, ATT&CK context, an investigation
narrative, recommendations, provider response IDs, and token usage.

## List incident investigations

`GET /api/v1/incidents/{incident_id}/investigations`

Results are ordered newest first. Updating an incident or attaching evidence
changes its context hash, allowing a new investigation while preserving earlier
results.

Telemetry is treated as untrusted input. The workflow excludes raw payloads,
size-bounds context, requires structured provider output, and rejects citations
that do not reference loaded incident, alert, event, attached-evidence, or MITRE
references. Structured network observations can produce a cited *reported*
exposure or segmentation-gap finding and a verification/change-control plan.
Blocked paths do not become exposure findings. Without relevant observations,
the result states that network exposure cannot be assessed. No active scan,
reachability test, firewall change, or autonomous remediation is performed.
Analyst-supplied evidence remains unverified even when a finding cites it; an
authorized operator must corroborate it and approve any production change.
Finding and narrative confidence is capped at 65% for analyst-supplied evidence
without corroborating telemetry, and 50% for incident reports alone. These are
guardrails, not calibrated probabilities.

This improves evidence handling, not a measured claim of real-world accuracy.
Evaluate against representative, labeled incidents from your own environment
before trusting detection or remediation rates. The design follows
[NIST SP 800-115](https://csrc.nist.gov/pubs/sp/800/115/final) for authorized
testing and mitigation, [CISA network hardening guidance](https://www.cisa.gov/resources-tools/resources/enhanced-visibility-and-hardening-guidance-communications-infrastructure)
for segmentation and access controls, and [OWASP guidance on prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
and [sensitive-information disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/).
