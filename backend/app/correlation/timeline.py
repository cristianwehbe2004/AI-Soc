from __future__ import annotations

from app.models.alert import Alert
from app.models.event import Event


def build_incident_timeline(alerts: list[Alert], events_by_id: dict) -> list[dict]:
    entries: list[dict] = []
    seen_event_ids: set[str] = set()

    for alert in sorted(alerts, key=lambda item: (item.first_seen, item.created_at)):
        event = events_by_id.get(alert.event_id)
        if event is not None and event.event_id not in seen_event_ids:
            seen_event_ids.add(event.event_id)
            entries.append(_event_entry(event))
        entries.append(_alert_entry(alert, event))

    entries.sort(key=lambda item: (item["timestamp"], item["type"]))
    return entries


def _event_entry(event: Event) -> dict:
    return {
        "timestamp": event.timestamp.isoformat(),
        "type": "event",
        "title": f"Event: {event.event_type}",
        "description": f"{event.source} generated a {event.event_type} event.",
        "event_id": event.event_id,
        "alert_id": None,
        "rule_id": None,
        "username": event.username,
        "source_ip": event.source_ip,
        "metadata": {
            "category": event.category,
            "status": event.status,
            "resource": event.resource,
            "bytes_received": event.bytes_received,
        },
    }


def _alert_entry(alert: Alert, event: Event | None) -> dict:
    return {
        "timestamp": alert.last_seen.isoformat(),
        "type": "alert",
        "title": alert.title,
        "description": alert.description,
        "event_id": event.event_id if event is not None else None,
        "alert_id": str(alert.id),
        "rule_id": alert.rule_id,
        "username": alert.username,
        "source_ip": alert.source_ip,
        "metadata": alert.evidence,
    }
