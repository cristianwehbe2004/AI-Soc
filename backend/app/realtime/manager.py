from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from contextlib import suppress

from fastapi import WebSocket
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


@dataclass
class RealtimeConnection:
    websocket: WebSocket
    queue: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(maxsize=100))


class RealtimeManager:
    def __init__(self, *, redis_url: str, channel_prefix: str, max_connections: int, max_message_bytes: int = 262144) -> None:
        self.redis_url = redis_url
        self.pattern = f"{channel_prefix.rstrip(':')}:*"
        self.max_connections = max_connections
        self.max_message_bytes = max_message_bytes
        self.connections: dict[int, RealtimeConnection] = {}
        self._redis: Redis | None = None
        self._pubsub = None
        self._listener: asyncio.Task | None = None

    async def start(self) -> None:
        if self._listener is not None:
            return
        self._redis = Redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
        self._pubsub = self._redis.pubsub()
        await self._pubsub.psubscribe(self.pattern)
        self._listener = asyncio.create_task(self._listen(), name="realtime-redis-listener")

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            await asyncio.gather(self._listener, return_exceptions=True)
            self._listener = None
        if self._pubsub is not None:
            await self._pubsub.aclose()
            self._pubsub = None
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
        for connection in list(self.connections.values()):
            await self.disconnect(connection.websocket)

    async def connect(self, websocket: WebSocket) -> RealtimeConnection | None:
        if len(self.connections) >= self.max_connections:
            await websocket.close(code=1013, reason="Realtime capacity reached")
            return None
        await websocket.accept()
        connection = RealtimeConnection(websocket=websocket)
        self.connections[id(websocket)] = connection
        return connection

    async def disconnect(self, websocket: WebSocket) -> None:
        self.connections.pop(id(websocket), None)
        try:
            await websocket.close()
        except Exception:
            pass

    async def _listen(self) -> None:
        assert self._pubsub is not None
        while True:
            try:
                async for message in self._pubsub.listen():
                    if message.get("type") != "pmessage":
                        continue
                    payload = message.get("data")
                    if not isinstance(payload, str):
                        continue
                    self._fan_out(payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Realtime Redis listener disconnected; reconnecting")
                await asyncio.sleep(1)
                if self._redis is None:
                    return
                with suppress(Exception):
                    await self._pubsub.aclose()
                self._pubsub = self._redis.pubsub()
                await self._pubsub.psubscribe(self.pattern)

    def _fan_out(self, payload: str) -> None:
        if len(payload.encode("utf-8")) > self.max_message_bytes:
            logger.warning("Dropping oversized realtime message")
            return
        for connection in list(self.connections.values()):
            try:
                connection.queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    connection.queue.get_nowait()
                    connection.queue.put_nowait(payload)
                except asyncio.QueueEmpty:
                    pass