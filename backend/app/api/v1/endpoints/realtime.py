from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.db.redis import redis_client
from app.db.session import SessionLocal
from app.realtime.manager import RealtimeManager
from app.realtime.tickets import RealtimeTicketStore
from app.repositories.auth_repository import AuthSessionRepository, UserRepository

router = APIRouter()
settings = get_settings()
manager = RealtimeManager(
    redis_url=settings.redis_url,
    channel_prefix=settings.realtime_redis_channel_prefix,
    max_connections=settings.realtime_max_connections,
    max_message_bytes=settings.realtime_max_message_bytes,
)


async def authenticate_ticket(ticket: str | None) -> uuid.UUID | None:
    if not ticket:
        return None
    ticket_identity = await RealtimeTicketStore(
        redis_client,
        key_prefix=settings.realtime_redis_channel_prefix,
        ttl_seconds=settings.realtime_ticket_ttl_seconds,
    ).consume(ticket)
    if ticket_identity is None:
        return None
    user_id, family_id = ticket_identity
    async with SessionLocal() as session:
        user = await UserRepository(session).get(user_id)
        if user is None or not user.is_active or not await AuthSessionRepository(session).family_is_active(family_id):
            return None
    return user_id


@router.websocket("/realtime")
async def realtime_socket(websocket: WebSocket) -> None:
    user_id = await authenticate_ticket(websocket.query_params.get("ticket"))
    if user_id is None:
        await websocket.close(code=4401, reason="Invalid realtime ticket")
        return
    connection = await manager.connect(websocket)
    if connection is None:
        return
    sender = asyncio.create_task(_send_messages(connection), name=f"realtime-send-{user_id}")
    heartbeat = asyncio.create_task(_heartbeat(websocket), name=f"realtime-heartbeat-{user_id}")
    try:
        await websocket.send_json({"type": "system.ready", "user_id": str(user_id)})
        while True:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > settings.realtime_max_message_bytes:
                await websocket.close(code=1009, reason="Message too large")
                return
            with suppress(json.JSONDecodeError):
                message = json.loads(raw)
                if message.get("type") == "pong":
                    continue
    except WebSocketDisconnect:
        pass
    finally:
        sender.cancel()
        heartbeat.cancel()
        await asyncio.gather(sender, heartbeat, return_exceptions=True)
        await manager.disconnect(websocket)


async def _send_messages(connection) -> None:
    while True:
        await connection.websocket.send_text(await connection.queue.get())


async def _heartbeat(websocket: WebSocket) -> None:
    while True:
        await asyncio.sleep(settings.realtime_heartbeat_seconds)
        await websocket.send_json({"type": "system.heartbeat"})