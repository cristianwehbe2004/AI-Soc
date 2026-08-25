import asyncio

from app.db.redis import ping_redis
from app.db.session import ping_database


async def main() -> None:
    for _ in range(30):
        try:
            if await ping_database() and await ping_redis():
                return
        except Exception:
            pass
        await asyncio.sleep(1)
    raise SystemExit("Database or Redis did not become ready in time.")


if __name__ == "__main__":
    asyncio.run(main())
