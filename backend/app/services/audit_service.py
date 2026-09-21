from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import Request

from app.models.auth import AuditLog
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.security.audit import request_metadata, sanitize_audit_details


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    async def record(
        self,
        *,
        request: Request,
        action: str,
        outcome: str,
        actor_type: str = "anonymous",
        actor_id: uuid.UUID | None = None,
        actor_label: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        return await self.repository.create(
            AuditLog(
                actor_type=actor_type,
                actor_id=actor_id,
                actor_label=actor_label,
                action=action,
                outcome=outcome,
                resource_type=resource_type,
                resource_id=resource_id,
                details=sanitize_audit_details(details or {}),
                **request_metadata(request),
            )
        )

    async def list(
        self,
        *,
        actor_type: str | None,
        actor_id: uuid.UUID | None,
        action: str | None,
        outcome: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
    ) -> AuditLogListResponse:
        rows, total = await self.repository.list(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            outcome=outcome,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        return AuditLogListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[AuditLogResponse.model_validate(row) for row in rows],
        )
