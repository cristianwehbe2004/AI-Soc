from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import AuthSession, Role, ServiceApiKey, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def list(self, *, limit: int, offset: int) -> tuple[list[User], int]:
        rows = await self.session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
        count = await self.session.scalar(select(func.count()).select_from(User))
        return list(rows.scalars()), int(count or 0)

    async def role_exists(self, role: str) -> bool:
        return await self.session.get(Role, role) is not None

    async def active_admin_count(self) -> int:
        count = await self.session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role_name == "admin", User.is_active.is_(True))
        )
        return int(count or 0)


class AuthSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, auth_session: AuthSession) -> AuthSession:
        self.session.add(auth_session)
        await self.session.flush()
        return auth_session

    async def get_for_update(self, session_id: uuid.UUID) -> AuthSession | None:
        result = await self.session.execute(
            select(AuthSession).where(AuthSession.id == session_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def family_is_active(self, family_id: uuid.UUID) -> bool:
        now = datetime.now(UTC)
        result = await self.session.scalar(
            select(func.count())
            .select_from(AuthSession)
            .where(
                AuthSession.family_id == family_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
        )
        return bool(result)

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        now = datetime.now(UTC)
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.family_id == family_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def revoke_user(self, user_id: uuid.UUID) -> None:
        now = datetime.now(UTC)
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )


class ApiKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, api_key: ServiceApiKey) -> ServiceApiKey:
        self.session.add(api_key)
        await self.session.flush()
        return api_key

    async def get(self, key_id: uuid.UUID) -> ServiceApiKey | None:
        return await self.session.get(ServiceApiKey, key_id)

    async def get_by_prefix(self, prefix: str) -> ServiceApiKey | None:
        result = await self.session.execute(
            select(ServiceApiKey).where(ServiceApiKey.prefix == prefix)
        )
        return result.scalar_one_or_none()

    async def list(self, *, limit: int, offset: int) -> tuple[list[ServiceApiKey], int]:
        rows = await self.session.execute(
            select(ServiceApiKey)
            .order_by(ServiceApiKey.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        count = await self.session.scalar(select(func.count()).select_from(ServiceApiKey))
        return list(rows.scalars()), int(count or 0)
