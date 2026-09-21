from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.auth import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.auth_repository import ApiKeyRepository
from app.schemas.auth import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyListResponse, ApiKeyResponse
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.services.api_key_service import ApiKeyService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api-keys")
AdminUser = Annotated[User, Depends(require_permission(Permission.API_KEYS_MANAGE))]


def get_api_key_service(session: AsyncSession = Depends(get_db_session)) -> ApiKeyService:
    return ApiKeyService(
        session,
        ApiKeyRepository(session),
        AuditService(AuditRepository(session)),
    )


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate,
    request: Request,
    actor: AdminUser,
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiKeyCreatedResponse:
    return await service.create(payload, actor, request)


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    actor: AdminUser,
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ApiKeyListResponse:
    return await service.list(limit=limit, offset=offset)


@router.post("/{key_id}/revoke", response_model=ApiKeyResponse)
async def revoke_api_key(
    key_id: uuid.UUID,
    request: Request,
    actor: AdminUser,
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiKeyResponse:
    result = await service.revoke(key_id, actor, request)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return result
