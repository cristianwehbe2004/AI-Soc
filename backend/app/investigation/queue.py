from __future__ import annotations

import uuid

from redis.asyncio import Redis


class InvestigationQueue:
    def __init__(self, redis: Redis, *, queue_key: str) -> None:
        self.redis = redis
        self.queue_key = queue_key

    async def enqueue(self, investigation_id: uuid.UUID) -> None:
        await self.redis.rpush(self.queue_key, str(investigation_id))

    async def dequeue(self, *, timeout: int) -> uuid.UUID | None:
        item = await self.redis.blpop(self.queue_key, timeout=timeout)
        if item is None:
            return None
        _, investigation_id = item
        return uuid.UUID(investigation_id)
