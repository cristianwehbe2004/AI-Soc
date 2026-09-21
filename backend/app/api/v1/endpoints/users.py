from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.auth import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.auth_repository import AuthSessionRepository, UserRepository
from app.schemas.auth import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.services.audit_service import AuditService
from app.services.user_service import LastAdminError, UserConflictError, UserService

router = APIRouter(prefix="/users")
AdminUser = Annotated[User, Depends(require_permission(Permission.USERS_MANAGE))]


def get_user_service(session: AsyncSession = Depends(get_db_session)) -> UserService:
    return UserService(
        session=session,
        users=UserRepository(session),
        sessions=AuthSessionRepository(session),
        audit=AuditService(AuditRepository(session)),
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    request: Request,
    actor: AdminUser,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    try:
        return await service.create(payload, actor, request)
    except UserConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=UserListResponse)
async def list_users(
    actor: AdminUser,
    service: Annotated[UserService, Depends(get_user_service)],
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> UserListResponse:
    return await service.list(limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    actor: AdminUser,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    result = await service.get(user_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return result


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    request: Request,
    actor: AdminUser,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    try:
        result = await service.update(
            user_id=user_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except LastAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return result
