from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import actor_context
from app.db.session import get_db_session
from app.models.auth import AuditLog, User
from app.repositories.auth_repository import ApiKeyRepository, AuthSessionRepository, UserRepository
from app.security.audit import request_metadata
from app.security.permissions import Permission, permissions_for_role
from app.security.tokens import InvalidAccessTokenError, decode_access_token, hash_secret, parse_api_key

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass(frozen=True)
class ServicePrincipal:
    id: uuid.UUID
    name: str
    prefix: str
    scopes: frozenset[str]


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    settings = get_settings()
    try:
        if not token:
            raise InvalidAccessTokenError("Missing token")
        claims = decode_access_token(token, settings)
        user = await UserRepository(session).get(claims["user_id"])
        family_active = await AuthSessionRepository(session).family_is_active(claims["family_id"])
        issued_at = datetime.fromtimestamp(claims["iat"], tz=UTC)
        if (
            user is None
            or not user.is_active
            or not family_active
            or issued_at < user.credentials_changed_at.replace(microsecond=0)
        ):
            raise InvalidAccessTokenError("Inactive identity")
    except InvalidAccessTokenError:
        await _audit_denial(session, request, actor_type="anonymous", action="authorization.authenticate")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    request.state.user = user
    actor_context.set(f"user:{user.id}")
    return user


def require_permission(permission: Permission):
    async def dependency(
        request: Request,
        user: Annotated[User, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if permission not in permissions_for_role(user.role_name):
            await _audit_denial(
                session,
                request,
                actor_type="user",
                actor_id=user.id,
                actor_label=user.email,
                action="authorization.denied",
                details={"permission": permission.value},
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return dependency


async def require_event_ingest_key(
    request: Request,
    value: Annotated[str | None, Security(api_key_header)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServicePrincipal:
    record = None
    try:
        if not value:
            raise ValueError
        prefix, secret = parse_api_key(value)
        record = await ApiKeyRepository(session).get_by_prefix(prefix)
        now = datetime.now(UTC)
        if (
            record is None
            or not record.is_active
            or record.revoked_at is not None
            or (record.expires_at is not None and record.expires_at <= now)
            or "events:write" not in record.scopes
            or not secrets.compare_digest(record.key_hash, hash_secret(secret))
        ):
            raise ValueError
    except ValueError:
        await _audit_denial(
            session,
            request,
            actor_type="api_key" if record else "anonymous",
            actor_id=record.id if record else None,
            actor_label=record.name if record else None,
            action="authorization.ingest_denied",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key") from None
    record.last_used_at = datetime.now(UTC)
    principal = ServicePrincipal(
        id=record.id,
        name=record.name,
        prefix=record.prefix,
        scopes=frozenset(record.scopes),
    )
    request.state.service_principal = principal
    actor_context.set(f"api_key:{record.id}")
    return principal


async def _audit_denial(
    session: AsyncSession,
    request: Request,
    *,
    actor_type: str,
    action: str,
    actor_id: uuid.UUID | None = None,
    actor_label: str | None = None,
    details: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            actor_label=actor_label,
            action=action,
            outcome="denied",
            details=details or {},
            **request_metadata(request),
        )
    )
    await session.commit()
