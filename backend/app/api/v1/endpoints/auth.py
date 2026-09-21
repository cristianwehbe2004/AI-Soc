from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.redis import redis_client
from app.db.session import get_db_session
from app.models.auth import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.auth_repository import AuthSessionRepository, UserRepository
from app.schemas.auth import ChangePasswordRequest, MessageResponse, TokenResponse, UserResponse
from app.security.dependencies import get_current_user
from app.security.rate_limit import LoginRateLimiter
from app.services.audit_service import AuditService
from app.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    LoginRateLimitedError,
    RefreshTokenError,
)

router = APIRouter(prefix="/auth")


def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    settings = get_settings()
    return AuthService(
        session=session,
        users=UserRepository(session),
        sessions=AuthSessionRepository(session),
        audit=AuditService(AuditRepository(session)),
        rate_limiter=LoginRateLimiter(redis_client, settings),
        settings=settings,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    try:
        result = await service.login(email=form.username, password=form.password, request=request)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except LoginRateLimitedError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    _set_refresh_cookie(response, result.refresh_token, get_settings())
    return result.response


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    settings = get_settings()
    try:
        result = await service.refresh(
            refresh_token=request.cookies.get(settings.auth_refresh_cookie_name),
            request=request,
        )
    except RefreshTokenError as exc:
        _clear_refresh_cookie(response, settings)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    _set_refresh_cookie(response, result.refresh_token, settings)
    return result.response


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    settings = get_settings()
    await service.logout(
        refresh_token=request.cookies.get(settings.auth_refresh_cookie_name),
        request=request,
    )
    _clear_refresh_cookie(response, settings)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    try:
        await service.change_password(user=user, payload=payload, request=request)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    _clear_refresh_cookie(response, get_settings())
    return MessageResponse(message="Password changed; all sessions revoked")


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=token,
        max_age=settings.auth_refresh_token_days * 86400,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth",
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth",
    )
