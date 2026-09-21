from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.auth import User
from app.repositories.audit_repository import AuditRepository
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
from app.security.dependencies import ServicePrincipal, require_event_ingest_key, require_permission
from app.security.permissions import Permission
from app.services.audit_service import AuditService

router = APIRouter(prefix="/events")
ReadUser = Annotated[User, Depends(require_permission(Permission.SOC_READ))]


def get_event_service(session: AsyncSession = Depends(get_db_session)) -> EventService:
    return EventService(session)


def get_audit_service(session: AsyncSession = Depends(get_db_session)) -> AuditService:
    return AuditService(AuditRepository(session))


@router.post("", response_model=EventIngestResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    request: Request,
    principal: Annotated[ServicePrincipal, Depends(require_event_ingest_key)],
    event_service: EventService = Depends(get_event_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> EventIngestResponse:
    result = await event_service.create_event(payload)
    await audit_service.record(
        request=request,
        action="events.ingest",
        outcome="success",
        actor_type="api_key",
        actor_id=principal.id,
        actor_label=principal.name,
        resource_type="event",
        resource_id=result.event_id,
        details={"count": 1},
    )
    await event_service.session.commit()
    return result


@router.post("/bulk", response_model=EventBulkIngestResponse, status_code=status.HTTP_201_CREATED)
async def create_events_bulk(
    payload: EventBulkCreate,
    request: Request,
    principal: Annotated[ServicePrincipal, Depends(require_event_ingest_key)],
    event_service: EventService = Depends(get_event_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> EventBulkIngestResponse:
    result = await event_service.create_events_bulk(payload)
    await audit_service.record(
        request=request,
        action="events.ingest_bulk",
        outcome="success",
        actor_type="api_key",
        actor_id=principal.id,
        actor_label=principal.name,
        resource_type="event",
        details={"count": result.count},
    )
    await event_service.session.commit()
    return result


@router.get("", response_model=EventListResponse)
async def list_events(
    actor: ReadUser,
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
    actor: ReadUser,
    event_service: EventService = Depends(get_event_service),
) -> EventResponse:
    event = await event_service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event
