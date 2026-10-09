from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.redis import redis_client
from app.db.session import get_db_session
from app.models.auth import User
from app.realtime.events import RealtimePublisher
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident_evidence import IncidentEvidenceCreate, IncidentEvidenceResponse
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.services.audit_service import AuditService
from app.services.incident_evidence import IncidentEvidenceError, add_evidence, list_evidence

router = APIRouter(prefix="/incidents", tags=["incident-evidence"])
Reader = Annotated[User, Depends(require_permission(Permission.SOC_READ))]
Analyst = Annotated[User, Depends(require_permission(Permission.INCIDENTS_WRITE))]


@router.get("/{incident_id}/evidence", response_model=list[IncidentEvidenceResponse])
async def get_evidence(incident_id: uuid.UUID, actor: Reader, session: AsyncSession = Depends(get_db_session)):
    if await IncidentRepository(session).get(incident_id) is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return await list_evidence(session, incident_id)


@router.post("/{incident_id}/evidence", response_model=IncidentEvidenceResponse, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    incident_id: uuid.UUID, payload: IncidentEvidenceCreate, request: Request, actor: Analyst,
    session: AsyncSession = Depends(get_db_session),
):
    try:
        row = await add_evidence(session, incident_id, actor.id, payload)
    except IncidentEvidenceError as exc:
        raise HTTPException(status_code=404 if str(exc) == "Incident not found" else 409, detail=str(exc)) from exc
    await AuditService(AuditRepository(session)).record(
        request=request, action="incident.evidence.add", outcome="success", actor_type="user",
        actor_id=actor.id, actor_label=actor.email, resource_type="incident_evidence", resource_id=str(row.id),
        details={"incident_id": str(incident_id), "kind": row.kind, "sensitive_redacted": row.sensitive_redacted},
    )
    await session.commit()
    try:
        await RealtimePublisher(redis_client, channel_prefix=get_settings().realtime_redis_channel_prefix).publish(
            "incident.evidence_added", entity_id=str(incident_id),
            payload={"incident_id": str(incident_id), "evidence_id": str(row.id)},
            version=int(row.created_at.timestamp() * 1_000_000),
        )
    except Exception:
        pass
    return row
