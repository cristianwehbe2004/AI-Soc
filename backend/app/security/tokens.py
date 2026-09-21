from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings


class InvalidAccessTokenError(ValueError):
    pass


def create_access_token(*, user_id: uuid.UUID, family_id: uuid.UUID, settings: Settings) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_in = settings.auth_access_token_minutes * 60
    payload = {
        "sub": str(user_id),
        "sid": str(family_id),
        "jti": str(uuid.uuid4()),
        "type": "access",
        "iss": settings.auth_jwt_issuer,
        "aud": settings.auth_jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256"), expires_in


def decode_access_token(token: str, settings: Settings) -> dict:
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            audience=settings.auth_jwt_audience,
            issuer=settings.auth_jwt_issuer,
            options={
                "require": ["sub", "sid", "jti", "type", "iss", "aud", "iat", "nbf", "exp"]
            },
        )
        if claims["type"] != "access":
            raise InvalidAccessTokenError("Unexpected token type")
        claims["user_id"] = uuid.UUID(claims["sub"])
        claims["family_id"] = uuid.UUID(claims["sid"])
        return claims
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessTokenError("Invalid access token") from exc


def generate_refresh_token(session_id: uuid.UUID) -> tuple[str, str]:
    secret = secrets.token_urlsafe(48)
    return f"{session_id}.{secret}", hash_secret(secret)


def parse_refresh_token(token: str) -> tuple[uuid.UUID, str]:
    try:
        raw_id, secret = token.split(".", 1)
        return uuid.UUID(raw_id), secret
    except (ValueError, AttributeError) as exc:
        raise ValueError("Invalid refresh token") from exc


def generate_api_key() -> tuple[str, str, str]:
    prefix = secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    return f"aisoc_{prefix}_{secret}", prefix, hash_secret(secret)


def parse_api_key(value: str) -> tuple[str, str]:
    try:
        marker, prefix, secret = value.split("_", 2)
        if marker != "aisoc" or not prefix or not secret:
            raise ValueError
        return prefix, secret
    except (ValueError, AttributeError) as exc:
        raise ValueError("Invalid API key") from exc


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()
