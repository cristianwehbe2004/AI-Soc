from app.db.redis import ping_redis
from app.db.session import ping_database
from app.schemas.health import HealthResponse


class HealthService:
    async def check(self) -> HealthResponse:
        database_ok = await self._safe_check(ping_database)
        redis_ok = await self._safe_check(ping_redis)

        overall_status = "healthy" if database_ok and redis_ok else "degraded"

        return HealthResponse(
            status=overall_status,
            database="connected" if database_ok else "disconnected",
            redis="connected" if redis_ok else "disconnected",
        )

    async def _safe_check(self, checker) -> bool:
        try:
            return await checker()
        except Exception:
            return False
