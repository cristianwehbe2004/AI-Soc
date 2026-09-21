from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.repositories.auth_repository import AuthSessionRepository, UserRepository
from app.schemas.auth import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.security.passwords import hash_password, normalize_email
from app.services.audit_service import AuditService


class UserConflictError(ValueError):
    pass


class LastAdminError(ValueError):
    pass


class UserService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        users: UserRepository,
        sessions: AuthSessionRepository,
        audit: AuditService,
    ) -> None:
        self.session = session
        self.users = users
        self.sessions = sessions
        self.audit = audit

    async def create(self, payload: UserCreate, actor: User, request: Request) -> UserResponse:
        email = normalize_email(str(payload.email))
        if await self.users.get_by_email(email) is not None:
            raise UserConflictError("A user with this email already exists")
        user = await self.users.create(
            User(
                email=email,
                full_name=payload.full_name.strip(),
                password_hash=hash_password(payload.password),
                role_name=payload.role_name,
                created_by=actor.id,
            )
        )
        await self.audit.record(
            request=request,
            action="user.create",
            outcome="success",
            actor_type="user",
            actor_id=actor.id,
            actor_label=actor.email,
            resource_type="user",
            resource_id=str(user.id),
            details={"email": user.email, "role": user.role_name},
        )
        await self.session.commit()
        return UserResponse.model_validate(user)

    async def get(self, user_id: uuid.UUID) -> UserResponse | None:
        user = await self.users.get(user_id)
        return UserResponse.model_validate(user) if user else None

    async def list(self, *, limit: int, offset: int) -> UserListResponse:
        users, total = await self.users.list(limit=limit, offset=offset)
        return UserListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[UserResponse.model_validate(user) for user in users],
        )

    async def update(
        self,
        *,
        user_id: uuid.UUID,
        payload: UserUpdate,
        actor: User,
        request: Request,
    ) -> UserResponse | None:
        user = await self.users.get(user_id)
        if user is None:
            return None
        removes_admin = user.role_name == "admin" and (
            payload.role_name not in {None, "admin"} or payload.is_active is False
        )
        if removes_admin and await self.users.active_admin_count() <= 1:
            raise LastAdminError("The last active administrator cannot be removed")
        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.role_name is not None:
            user.role_name = payload.role_name
        if payload.is_active is not None:
            user.is_active = payload.is_active
        user.updated_at = datetime.now(UTC)
        if payload.is_active is False or payload.role_name is not None:
            await self.sessions.revoke_user(user.id)
        await self.audit.record(
            request=request,
            action="user.update",
            outcome="success",
            actor_type="user",
            actor_id=actor.id,
            actor_label=actor.email,
            resource_type="user",
            resource_id=str(user.id),
            details=payload.model_dump(exclude_none=True),
        )
        await self.session.commit()
        return UserResponse.model_validate(user)
