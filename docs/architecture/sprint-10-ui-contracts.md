# Sprint 10 UI Contracts

Sprint 9.5 establishes the backend contracts that the SOC UI can build against.

## Decisions

- Dashboard KPIs use `GET /api/v1/dashboard/summary` so the dashboard does not coordinate multiple aggregate queries.
- Alerts remain incident-scoped in `IncidentDetail`; a standalone alert list/detail workflow is deferred until an analyst workflow requires it.
- Analyst notes are persisted by incident at `GET|POST /api/v1/incidents/{incident_id}/notes` and updated with `PATCH /api/v1/incidents/{incident_id}/notes/{note_id}`. Analysts and administrators can write notes; viewers can read them.
- ML evidence is exposed at `GET /api/v1/incidents/{incident_id}/ml`. The response explicitly reports unavailable model state instead of making the UI infer it from an error.
- Incident detail owns the timeline, alerts, MITRE techniques, ML panel, AI investigations, and analyst notes.

## Frontend Resource Boundaries

- Dashboard: summary KPIs and model availability.
- Events: paginated list and event detail.
- Incidents: filtered list and incident detail.
- Incident detail panels: timeline, alerts, MITRE, ML, investigations, and notes.
- MITRE: standalone technique catalog and rule-to-technique lookup.
- Investigations: incident-scoped list, request action, and investigation detail.