import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.config import get_settings
from app.db.redis import redis_client
from app.db.session import get_db_session

from app.models.auth import User
from app.realtime.events import RealtimePublisher
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.mitre_repository import MitreRepository
from app.repositories.note_repository import IncidentNoteRepository
from app.schemas.incident import (
    IncidentCreate,
    IncidentDetail,
    IncidentListItem,
    IncidentListResponse,
    IncidentQueryFilters,
    IncidentSeverity,
    IncidentStatus,
)
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.services.audit_service import AuditService
from app.services.incident_service import IncidentService

router = APIRouter(
    prefix="/incidents",
    dependencies=[Depends(require_permission(Permission.SOC_READ))],
)
AnalystUser = Annotated[User, Depends(require_permission(Permission.INCIDENTS_WRITE))]


def get_incident_service(session: AsyncSession = Depends(get_db_session)) -> IncidentService:
    return IncidentService(
        IncidentRepository(session), MitreRepository(session), IncidentNoteRepository(session)
    )


def get_audit_service(session: AsyncSession = Depends(get_db_session)) -> AuditService:
    return AuditService(AuditRepository(session))


@router.post("", response_model=IncidentDetail, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate,
    request: Request,
    actor: AnalystUser,
    incident_service: IncidentService = Depends(get_incident_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> IncidentDetail:
    if payload.preset_scenario != "custom" and get_settings().app_env.lower() not in {"development", "test"}:
        raise HTTPException(status_code=400, detail="Demo incident presets are disabled outside development/test")
    result = await incident_service.create_manual_incident(payload)
    await audit_service.record(
        request=request,
        action="incident.create",
        outcome="success",
        actor_type="user",
        actor_id=actor.id,
        actor_label=actor.email,
        resource_type="incident",
        resource_id=str(result.id),
        details={"preset": payload.preset_scenario},
    )
    await incident_service.incident_repository.session.commit()
    try:
        await RealtimePublisher(
            redis_client,
            channel_prefix=get_settings().realtime_redis_channel_prefix,
        ).publish(
            "incident.created",
            entity_id=str(result.id),
            payload=IncidentListItem.model_validate(result).model_dump(mode="json"),
        )
    except Exception:
        pass
    return result


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    severity: IncidentSeverity | None = Query(default=None),
    username: str | None = Query(default=None),
    source_ip: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentListResponse:
    filters = IncidentQueryFilters(
        status=status_filter,
        severity=severity,
        username=username,
        source_ip=source_ip,
        limit=limit,
        offset=offset,
    )
    return await incident_service.list_incidents(filters)


@router.get("/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: uuid.UUID,
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentDetail:
    incident = await incident_service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident
