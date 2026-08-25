from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.event import (
    EventBulkCreate,
    EventBulkIngestResponse,
    EventCategory,
    EventCreate,
    EventIngestResponse,
    EventListResponse,
    EventQueryFilters,
    EventResponse,
    EventSeverity,
    EventType,
)
from app.services.event_service import EventService

router = APIRouter(prefix="/events")


def get_event_service(session: AsyncSession = Depends(get_db_session)) -> EventService:
    return EventService(session)


@router.post("", response_model=EventIngestResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    event_service: EventService = Depends(get_event_service),
) -> EventIngestResponse:
    return await event_service.create_event(payload)


@router.post("/bulk", response_model=EventBulkIngestResponse, status_code=status.HTTP_201_CREATED)
async def create_events_bulk(
    payload: EventBulkCreate,
    event_service: EventService = Depends(get_event_service),
) -> EventBulkIngestResponse:
    return await event_service.create_events_bulk(payload)


@router.get("", response_model=EventListResponse)
async def list_events(
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    event_type: EventType | None = Query(default=None),
    category: EventCategory | None = Query(default=None),
    source_ip: str | None = Query(default=None),
    username: str | None = Query(default=None),
    severity: EventSeverity | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    event_service: EventService = Depends(get_event_service),
) -> EventListResponse:
    filters = EventQueryFilters(
        start_time=start_time,
        end_time=end_time,
        event_type=event_type,
        category=category,
        source_ip=source_ip,
        username=username,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    return await event_service.list_events(filters)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    event_service: EventService = Depends(get_event_service),
) -> EventResponse:
    event = await event_service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event
