from __future__ import annotations

import hashlib
import secrets
import uuid

from redis.asyncio import Redis


class RealtimeTicketStore:
    def __init__(self, redis: Redis, *, key_prefix: str, ttl_seconds: int) -> None:
        self.redis = redis
        self.key_prefix = key_prefix.rstrip(":")
        self.ttl_seconds = ttl_seconds

    async def issue(self, user_id: uuid.UUID, family_id: uuid.UUID) -> str:
        ticket = secrets.token_urlsafe(32)
        await self.redis.setex(
            self._key(ticket),
            self.ttl_seconds,
            f"{user_id}:{family_id}",
        )
        return ticket

    async def consume(self, ticket: str) -> uuid.UUID | None:
        value = await self.redis.getdel(self._key(ticket))
        if not value:
            return None
        try:
            user_id, family_id = value.split(":", 1)
            return uuid.UUID(user_id), uuid.UUID(family_id)
        except (ValueError, AttributeError):
            return None

    def _key(self, ticket: str) -> str:
        digest = hashlib.sha256(ticket.encode("utf-8")).hexdigest()
        return f"{self.key_prefix}:ticket:{digest}"