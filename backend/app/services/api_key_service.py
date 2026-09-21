from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import ServiceApiKey, User
from app.repositories.auth_repository import ApiKeyRepository
from app.schemas.auth import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
)
from app.security.tokens import generate_api_key
from app.services.audit_service import AuditService


class ApiKeyService:
    def __init__(self, session: AsyncSession, repository: ApiKeyRepository, audit: AuditService) -> None:
        self.session = session
        self.repository = repository
        self.audit = audit

    async def create(
        self, payload: ApiKeyCreate, actor: User, request: Request
    ) -> ApiKeyCreatedResponse:
        raw_key, prefix, key_hash = generate_api_key()
        record = await self.repository.create(
            ServiceApiKey(
                name=payload.name.strip(),
                prefix=prefix,
                key_hash=key_hash,
                scopes=list(dict.fromkeys(payload.scopes)),
                expires_at=payload.expires_at,
                created_by=actor.id,
            )
        )
        await self.audit.record(
            request=request,
            action="api_key.create",
            outcome="success",
            actor_type="user",
            actor_id=actor.id,
            actor_label=actor.email,
            resource_type="api_key",
            resource_id=str(record.id),
            details={"name": record.name, "prefix": record.prefix, "scopes": record.scopes},
        )
        await self.session.commit()
        return ApiKeyCreatedResponse(
            **ApiKeyResponse.model_validate(record).model_dump(), api_key=raw_key
        )

    async def list(self, *, limit: int, offset: int) -> ApiKeyListResponse:
        keys, total = await self.repository.list(limit=limit, offset=offset)
        return ApiKeyListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[ApiKeyResponse.model_validate(item) for item in keys],
        )

    async def revoke(
        self, key_id: uuid.UUID, actor: User, request: Request
    ) -> ApiKeyResponse | None:
        record = await self.repository.get(key_id)
        if record is None:
            return None
        if record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
            record.is_active = False
        await self.audit.record(
            request=request,
            action="api_key.revoke",
            outcome="success",
            actor_type="user",
            actor_id=actor.id,
            actor_label=actor.email,
            resource_type="api_key",
            resource_id=str(record.id),
        )
        await self.session.commit()
        return ApiKeyResponse.model_validate(record)
