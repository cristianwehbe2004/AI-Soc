from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from app.models.event import Event
from app.schemas.event import EventCreate


class EventNormalizer(Protocol):
    def normalize(self, payload: EventCreate) -> Event: ...


class GenericJSONNormalizer:
    def normalize(self, payload: EventCreate) -> Event:
        raw_payload = payload.raw_payload or payload.model_dump(mode="json", exclude_none=True)

        return Event(
            event_id=payload.event_id or f"evt_{uuid.uuid4().hex}",
            timestamp=self._normalize_timestamp(payload.timestamp),
            received_at=datetime.now(UTC),
            source=payload.source,
            source_type=payload.source_type,
            event_type=payload.event_type,
            category=payload.category,
            severity=payload.severity,
            user_id=payload.user_id,
            username=payload.username,
            source_ip=payload.source_ip,
            destination_ip=payload.destination_ip,
            source_port=payload.source_port,
            destination_port=payload.destination_port,
            hostname=payload.hostname,
            device_id=payload.device_id,
            action=payload.action,
            status=payload.status,
            resource=payload.resource,
            resource_type=payload.resource_type,
            country=payload.country,
            user_agent=payload.user_agent,
            bytes_sent=payload.bytes_sent,
            bytes_received=payload.bytes_received,
            raw_payload=raw_payload,
            event_metadata=payload.metadata,
            created_at=datetime.now(UTC),
        )

    def _normalize_timestamp(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def get_normalizer(_: EventCreate | dict[str, Any]) -> EventNormalizer:
    return GenericJSONNormalizer()
