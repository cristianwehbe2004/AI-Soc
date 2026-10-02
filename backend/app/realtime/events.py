from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from redis.asyncio import Redis


CHANNELS = {
    "event": "events",
    "alert": "alerts",
    "incident": "incidents",
    "investigation": "investigations",
}


class RealtimeEnvelope(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    type: str
    entity_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = 1
    payload: dict[str, Any]


class RealtimePublisher:
    def __init__(self, redis: Redis, *, channel_prefix: str) -> None:
        self.redis = redis
        self.channel_prefix = channel_prefix.rstrip(":")

    async def publish(
        self,
        event_type: str,
        *,
        entity_id: str,
        payload: dict[str, Any],
        version: int = 1,
    ) -> RealtimeEnvelope:
        envelope = RealtimeEnvelope(
            type=event_type,
            entity_id=entity_id,
            payload=payload,
            version=version,
        )
        channel_group = event_type.split(".", 1)[0]
        channel = f"{self.channel_prefix}:{CHANNELS.get(channel_group, 'system')}"
        await self.redis.publish(channel, envelope.model_dump_json())
        return envelope