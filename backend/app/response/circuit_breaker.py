from __future__ import annotations

import time
from typing import Any


class CircuitBreaker:
    """
    Manages autonomous response rate limits and the global kill switch.
    Supports in-memory tracking or Redis for distributed state.
    """

    def __init__(
        self,
        redis: Any | None = None,
        *,
        max_actions_per_hour: int = 10,
        max_disruptive_actions_per_hour: int = 3,
        key_prefix: str = "ai_soc:circuit_breaker",
    ) -> None:
        self.redis = redis
        self.max_actions_per_hour = max_actions_per_hour
        self.max_disruptive_actions_per_hour = max_disruptive_actions_per_hour
        self.key_prefix = key_prefix
        # In-memory fallbacks when Redis is not supplied (e.g. unit tests)
        self._local_kill_switch: bool = False
        self._local_history: list[tuple[float, str]] = []

    async def is_tripped(self) -> tuple[bool, str]:
        """Checks if the global kill switch or rate limits have tripped."""
        if self.redis is not None:
            halted = await self.redis.get(f"{self.key_prefix}:kill_switch")
            if halted and halted.decode() == "1":
                return True, "Global response kill switch is ACTIVE"
            
            total_count = await self._redis_count(f"{self.key_prefix}:all_actions")
            if total_count >= self.max_actions_per_hour:
                return True, f"Hourly total action cap reached ({total_count}/{self.max_actions_per_hour})"

            disruptive_count = await self._redis_count(f"{self.key_prefix}:disruptive_actions")
            if disruptive_count >= self.max_disruptive_actions_per_hour:
                return True, f"Hourly disruptive action cap reached ({disruptive_count}/{self.max_disruptive_actions_per_hour})"
            return False, "ok"

        # In-memory implementation
        if self._local_kill_switch:
            return True, "Global response kill switch is ACTIVE"

        now = time.time()
        one_hour_ago = now - 3600
        self._local_history = [(t, kind) for t, kind in self._local_history if t >= one_hour_ago]

        total = len(self._local_history)
        if total >= self.max_actions_per_hour:
            return True, f"Hourly total action cap reached ({total}/{self.max_actions_per_hour})"

        disruptive = sum(1 for _, kind in self._local_history if kind == "disruptive")
        if disruptive >= self.max_disruptive_actions_per_hour:
            return True, f"Hourly disruptive action cap reached ({disruptive}/{self.max_disruptive_actions_per_hour})"

        return False, "ok"

    async def record_execution(self, *, is_disruptive: bool) -> None:
        """Records an executed action towards the sliding hour limit."""
        if self.redis is not None:
            now = time.time()
            pipe = self.redis.pipeline()
            # Redis sorted sets for sliding window
            pipe.zadd(f"{self.key_prefix}:all_actions", {str(now): now})
            pipe.expire(f"{self.key_prefix}:all_actions", 3600)
            if is_disruptive:
                pipe.zadd(f"{self.key_prefix}:disruptive_actions", {str(now): now})
                pipe.expire(f"{self.key_prefix}:disruptive_actions", 3600)
            await pipe.execute()
            return

        self._local_history.append((time.time(), "disruptive" if is_disruptive else "normal"))

    async def set_kill_switch(self, enabled: bool) -> None:
        """Activates or deactivates the emergency response kill switch."""
        if self.redis is not None:
            await self.redis.set(f"{self.key_prefix}:kill_switch", "1" if enabled else "0")
        else:
            self._local_kill_switch = enabled

    async def _redis_count(self, key: str) -> int:
        now = time.time()
        one_hour_ago = now - 3600
        # Remove old elements then count
        await self.redis.zremrangebyscore(key, 0, one_hour_ago)
        return await self.redis.zcard(key)
