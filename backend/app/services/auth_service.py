from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.auth import AuthSession, User
from app.repositories.auth_repository import AuthSessionRepository, UserRepository
from app.schemas.auth import ChangePasswordRequest, TokenResponse, UserResponse
from app.security.passwords import hash_password, normalize_email, verify_password
from app.security.rate_limit import LoginRateLimiter
from app.security.tokens import (
    create_access_token,
    generate_refresh_token,
    hash_secret,
    parse_refresh_token,
)
from app.services.audit_service import AuditService

DUMMY_PASSWORD_HASH = hash_password("dummy-password-never-used")


class InvalidCredentialsError(ValueError):
    pass


class LoginRateLimitedError(ValueError):
    pass


class RefreshTokenError(ValueError):
    pass


@dataclass(frozen=True)
class AuthenticationResult:
    response: TokenResponse
    refresh_token: str


class AuthService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        users: UserRepository,
        sessions: AuthSessionRepository,
        audit: AuditService,
        rate_limiter: LoginRateLimiter,
        settings: Settings,
    ) -> None:
        self.session = session
        self.users = users
        self.sessions = sessions
        self.audit = audit
        self.rate_limiter = rate_limiter
        self.settings = settings

    async def login(self, *, email: str, password: str, request: Request) -> AuthenticationResult:
        normalized = normalize_email(email)
        source_ip = request.client.host if request.client else "unknown"
        if await self.rate_limiter.is_limited(normalized, source_ip):
            await self.audit.record(
                request=request,
                action="auth.login",
                outcome="rate_limited",
                actor_label=normalized,
            )
            await self.session.commit()
            raise LoginRateLimitedError("Too many authentication attempts")

        user = await self.users.get_by_email(normalized)
        valid_password = verify_password(
            password,
            user.password_hash if user is not None else DUMMY_PASSWORD_HASH,
        )
        if user is None or not valid_password or not user.is_active:
            await self.rate_limiter.record_failure(normalized, source_ip)
            await self.audit.record(
                request=request,
                action="auth.login",
                outcome="failure",
                actor_id=user.id if user else None,
                actor_label=normalized,
            )
            await self.session.commit()
            raise InvalidCredentialsError("Invalid email or password")

        result = await self._new_session(user=user, request=request)
        user.last_login_at = datetime.now(UTC)
        await self.rate_limiter.clear_account(normalized)
        await self.audit.record(
            request=request,
            action="auth.login",
            outcome="success",
            actor_type="user",
            actor_id=user.id,
            actor_label=user.email,
        )
        await self.session.commit()
        return result

    async def refresh(self, *, refresh_token: str | None, request: Request) -> AuthenticationResult:
        try:
            session_id, secret = parse_refresh_token(refresh_token or "")
        except ValueError:
            await self._audit_refresh_failure(request)
            raise RefreshTokenError("Invalid refresh token") from None

        auth_session = await self.sessions.get_for_update(session_id)
        if auth_session is None or not secrets.compare_digest(
            auth_session.token_hash, hash_secret(secret)
        ):
            await self._audit_refresh_failure(request)
            raise RefreshTokenError("Invalid refresh token")

        if auth_session.revoked_at is not None:
            await self.sessions.revoke_family(auth_session.family_id)
            await self.audit.record(
                request=request,
                action="auth.refresh_reuse",
                outcome="failure",
                actor_type="user",
                actor_id=auth_session.user_id,
            )
            await self.session.commit()
            raise RefreshTokenError("Invalid refresh token")

        now = datetime.now(UTC)
        user = await self.users.get(auth_session.user_id)
        if auth_session.expires_at <= now or user is None or not user.is_active:
            await self.sessions.revoke_family(auth_session.family_id)
            await self._audit_refresh_failure(request, user=user)
            raise RefreshTokenError("Invalid refresh token")

        replacement_id = uuid.uuid4()
        raw_token, token_hash = generate_refresh_token(replacement_id)
        replacement = AuthSession(
            id=replacement_id,
            family_id=auth_session.family_id,
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(days=self.settings.auth_refresh_token_days),
            source_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:512] or None,
        )
        auth_session.revoked_at = now
        auth_session.last_used_at = now
        auth_session.replaced_by_id = replacement_id
        await self.sessions.create(replacement)
        access_token, expires_in = create_access_token(
            user_id=user.id,
            family_id=auth_session.family_id,
            settings=self.settings,
        )
        await self.audit.record(
            request=request,
            action="auth.refresh",
            outcome="success",
            actor_type="user",
            actor_id=user.id,
            actor_label=user.email,
        )
        await self.session.commit()
        return AuthenticationResult(
            response=TokenResponse(
                access_token=access_token,
                expires_in=expires_in,
                user=UserResponse.model_validate(user),
            ),
            refresh_token=raw_token,
        )

    async def logout(self, *, refresh_token: str | None, request: Request) -> None:
        actor_id = None
        try:
            session_id, secret = parse_refresh_token(refresh_token or "")
            auth_session = await self.sessions.get_for_update(session_id)
            if auth_session is not None and secrets.compare_digest(
                auth_session.token_hash, hash_secret(secret)
            ):
                actor_id = auth_session.user_id
                await self.sessions.revoke_family(auth_session.family_id)
        except ValueError:
            pass
        await self.audit.record(
            request=request,
            action="auth.logout",
            outcome="success",
            actor_type="user" if actor_id else "anonymous",
            actor_id=actor_id,
        )
        await self.session.commit()

    async def change_password(
        self,
        *,
        user: User,
        payload: ChangePasswordRequest,
        request: Request,
    ) -> None:
        if not verify_password(payload.current_password, user.password_hash):
            await self.audit.record(
                request=request,
                action="auth.password_change",
                outcome="failure",
                actor_type="user",
                actor_id=user.id,
                actor_label=user.email,
            )
            await self.session.commit()
            raise InvalidCredentialsError("Current password is incorrect")
        user.password_hash = hash_password(payload.new_password)
        user.credentials_changed_at = datetime.now(UTC)
        await self.sessions.revoke_user(user.id)
        await self.audit.record(
            request=request,
            action="auth.password_change",
            outcome="success",
            actor_type="user",
            actor_id=user.id,
            actor_label=user.email,
        )
        await self.session.commit()

    async def _new_session(self, *, user: User, request: Request) -> AuthenticationResult:
        session_id = uuid.uuid4()
        family_id = uuid.uuid4()
        raw_token, token_hash = generate_refresh_token(session_id)
        await self.sessions.create(
            AuthSession(
                id=session_id,
                family_id=family_id,
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(UTC) + timedelta(days=self.settings.auth_refresh_token_days),
                source_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent", "")[:512] or None,
            )
        )
        access_token, expires_in = create_access_token(
            user_id=user.id, family_id=family_id, settings=self.settings
        )
        return AuthenticationResult(
            response=TokenResponse(
                access_token=access_token,
                expires_in=expires_in,
                user=UserResponse.model_validate(user),
            ),
            refresh_token=raw_token,
        )

    async def _audit_refresh_failure(self, request: Request, user: User | None = None) -> None:
        await self.audit.record(
            request=request,
            action="auth.refresh",
            outcome="failure",
            actor_type="user" if user else "anonymous",
            actor_id=user.id if user else None,
            actor_label=user.email if user else None,
        )
        await self.session.commit()
