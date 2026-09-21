from __future__ import annotations

import hashlib

from redis.asyncio import Redis

from app.core.config import Settings


class LoginRateLimiter:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def is_limited(self, email: str, source_ip: str) -> bool:
        account, ip = await self.redis.mget(self._account_key(email), self._ip_key(source_ip))
        return int(account or 0) >= self.settings.auth_login_account_limit or int(
            ip or 0
        ) >= self.settings.auth_login_ip_limit

    async def record_failure(self, email: str, source_ip: str) -> None:
        for key in (self._account_key(email), self._ip_key(source_ip)):
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, self.settings.auth_login_window_seconds)

    async def clear_account(self, email: str) -> None:
        await self.redis.delete(self._account_key(email))

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _account_key(self, email: str) -> str:
        return f"ai_soc:auth:account:{self._digest(email)}"

    def _ip_key(self, source_ip: str) -> str:
        return f"ai_soc:auth:ip:{self._digest(source_ip)}"
