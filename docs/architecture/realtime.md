# Realtime Contract

The SOC uses Redis Pub/Sub for low-latency notifications and PostgreSQL as the
source of truth. Pub/Sub messages are advisory: clients invalidate or refresh
their REST queries after receiving a message.

## Channels

The configured prefix defaults to `ai_soc:realtime`.

- `ai_soc:realtime:events`
- `ai_soc:realtime:alerts`
- `ai_soc:realtime:incidents`
- `ai_soc:realtime:investigations`
- `ai_soc:realtime:responses`

## Envelope

```json
{
  "id": "message-uuid",
  "type": "incident.updated",
  "entity_id": "incident-uuid",
  "occurred_at": "2026-10-01T12:00:00Z",
  "version": 4,
  "payload": {}
}
```

The frontend drops duplicate message IDs and ignores an older version for the
same event type and entity. Broadcasts are emitted after the database commit;
publication failure is logged and does not roll back persisted telemetry.

## Message types

- `event.created`: emitted after single or bulk event ingestion commits.
- `alert.created`: emitted after detection alerts are persisted.
- `incident.created`: emitted when correlation creates an incident.
- `incident.updated`: emitted when correlation recalculates an existing incident.
- `investigation.queued`: emitted after an investigation request commits.
- `investigation.running`: emitted after the worker claims a job.
- `investigation.completed`: emitted after a worker result commits.
- `investigation.failed`: emitted after a worker failure commits.
- `response.proposed`, `response.approved`, `response.rejected`, `response.running`, `response.succeeded`, `response.failed`: emitted after response state changes. Payloads contain only incident ID, action type, and status; no secrets or raw evidence.

## Authentication

The browser first calls `POST /api/v1/auth/realtime-ticket` using its normal
access token. The backend issues a one-time Redis-backed ticket bound to the
active authentication session family. The browser then connects to
`/api/v1/realtime?ticket=...`. The ticket expires after 60 seconds and is
consumed on connection, so the long-lived access token is never placed in the
WebSocket URL.
The handshake checks the browser Origin allowlist (`REALTIME_ALLOWED_ORIGINS`),
and heartbeats revalidate the user and session family. Configure the production
frontend origin explicitly; the local defaults are not production settings.

## Delivery

Each backend process subscribes to the Redis channel pattern and fans messages
out to its local authenticated connections. Connections have bounded queues;
when a slow client queue is full, the oldest notification is dropped because
the REST API remains authoritative. Clients reconnect with bounded exponential
backoff and refetch current state after reconnecting.
