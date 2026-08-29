from __future__ import annotations

from datetime import timedelta

from app.models.event import Event
from app.repositories.event_repository import EventRepository


async def event_window(
    repository: EventRepository,
    event: Event,
    *,
    window_seconds: int,
) -> list[Event]:
    return await repository.list_between(
        start_time=event.timestamp - timedelta(seconds=window_seconds),
        end_time=event.timestamp,
    )
