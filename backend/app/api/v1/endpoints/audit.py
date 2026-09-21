from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.auth import User
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogListResponse
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs")
AdminUser = Annotated[User, Depends(require_permission(Permission.AUDIT_READ))]


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    actor: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    actor_type: str | None = Query(default=None),
    actor_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> AuditLogListResponse:
    return await AuditService(AuditRepository(session)).list(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        outcome=outcome,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
