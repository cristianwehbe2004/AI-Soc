from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.incident_repository import IncidentRepository
from app.repositories.mitre_repository import MitreRepository
from app.schemas.incident import IncidentDetail, IncidentListResponse, IncidentQueryFilters, IncidentSeverity, IncidentStatus
from app.services.incident_service import IncidentService
from app.security.dependencies import require_permission
from app.security.permissions import Permission

router = APIRouter(
    prefix="/incidents",
    dependencies=[Depends(require_permission(Permission.SOC_READ))],
)


def get_incident_service(session: AsyncSession = Depends(get_db_session)) -> IncidentService:
    return IncidentService(IncidentRepository(session), MitreRepository(session))


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
