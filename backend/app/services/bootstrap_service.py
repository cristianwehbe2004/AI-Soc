from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.repositories.auth_repository import UserRepository
from app.security.passwords import hash_password, normalize_email


async def create_first_admin(
    session: AsyncSession,
    *,
    email: str,
    full_name: str,
    password: str,
) -> bool:
    normalized_email = normalize_email(email)
    repository = UserRepository(session)
    existing = await repository.get_by_email(normalized_email)
    if existing is not None:
        if existing.role_name == "admin" and existing.is_active:
            return False
        raise RuntimeError("A non-active-admin user already uses this email")
    await repository.create(
        User(
            email=normalized_email,
            full_name=full_name.strip(),
            password_hash=hash_password(password),
            role_name="admin",
            created_by=None,
        )
    )
    await session.commit()
    return True
