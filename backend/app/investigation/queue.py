from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime

from redis.asyncio import Redis

CANCEL_KEY_PREFIX = "ai_soc:inv_cancel:"


class InvestigationQueue:
    def __init__(self, redis: Redis, *, queue_key: str) -> None:
        self.redis = redis
        self.queue_key = queue_key
        self.delayed_key = f"{queue_key}:delayed"
        self.dlq_key = f"{queue_key}:dlq"

    async def enqueue(self, investigation_id: uuid.UUID) -> None:
        await self.redis.rpush(self.queue_key, str(investigation_id))

    async def enqueue_delayed(
        self,
        investigation_id: uuid.UUID,
        *,
        delay_seconds: int,
    ) -> None:
        ready_ts = time.time() + delay_seconds
        await self.redis.zadd(self.delayed_key, {str(investigation_id): ready_ts})

    async def promote_delayed(self) -> int:
        now = time.time()
        ready_items = await self.redis.zrangebyscore(self.delayed_key, 0, now)
        promoted = 0
        for item in ready_items:
            removed = await self.redis.zrem(self.delayed_key, item)
            if removed > 0:
                item_str = item.decode("utf-8") if isinstance(item, bytes) else str(item)
                await self.redis.rpush(self.queue_key, item_str)
                promoted += 1
        return promoted

    async def dequeue(self, *, timeout: int) -> uuid.UUID | None:
        item = await self.redis.blpop(self.queue_key, timeout=timeout)
        if item is None:
            return None
        _, raw_id = item
        id_str = raw_id.decode("utf-8") if isinstance(raw_id, bytes) else str(raw_id)
        return uuid.UUID(id_str)

    async def send_to_dlq(
        self,
        investigation_id: uuid.UUID,
        *,
        reason: str,
        error_class: str = "permanent",
    ) -> None:
        payload = json.dumps({
            "id": str(investigation_id),
            "reason": reason[:2000],
            "error_class": error_class,
            "ts": datetime.now(UTC).isoformat(),
        })
        await self.redis.rpush(self.dlq_key, payload)

    async def list_dlq(self, *, count: int = 100) -> list[dict]:
        items = await self.redis.lrange(self.dlq_key, 0, count - 1)
        res = []
        for raw in items:
            raw_str = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            try:
                res.append(json.loads(raw_str))
            except Exception:
                res.append({"raw": raw_str})
        return res

    async def replay_from_dlq(self, investigation_id: uuid.UUID) -> bool:
        target_str = str(investigation_id)
        items = await self.redis.lrange(self.dlq_key, 0, -1)
        found = False
        for raw in items:
            raw_str = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            try:
                parsed = json.loads(raw_str)
                if parsed.get("id") == target_str:
                    await self.redis.lrem(self.dlq_key, 1, raw)
                    found = True
                    break
            except Exception:
                continue
        if found:
            await self.enqueue(investigation_id)
        return found

    async def request_cancel(self, investigation_id: uuid.UUID) -> None:
        key = f"{CANCEL_KEY_PREFIX}{investigation_id}"
        await self.redis.set(key, "1", ex=3600)

    async def is_cancelled(self, investigation_id: uuid.UUID) -> bool:
        key = f"{CANCEL_KEY_PREFIX}{investigation_id}"
        val = await self.redis.exists(key)
        return val > 0

    async def clear_cancel(self, investigation_id: uuid.UUID) -> None:
        key = f"{CANCEL_KEY_PREFIX}{investigation_id}"
        await self.redis.delete(key)
