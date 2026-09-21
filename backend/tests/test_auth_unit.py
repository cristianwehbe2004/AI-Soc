from __future__ import annotations

import uuid

import pytest

from app.core.config import get_settings
from app.security.audit import sanitize_audit_details
from app.security.passwords import hash_password, normalize_email, verify_password
from app.security.permissions import Permission, permissions_for_role
from app.security.rate_limit import LoginRateLimiter
from app.security.tokens import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    generate_api_key,
    generate_refresh_token,
    parse_api_key,
    parse_refresh_token,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def mget(self, *keys):
        return [self.values.get(key) for key in keys]

    async def incr(self, key):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    async def expire(self, key, seconds):
        self.expirations[key] = seconds

    async def delete(self, key):
        self.values.pop(key, None)


def test_password_hashing_and_email_normalization() -> None:
    encoded = hash_password("Correct-Horse-Battery-1")

    assert normalize_email("  Analyst@Example.COM ") == "analyst@example.com"
    assert verify_password("Correct-Horse-Battery-1", encoded)
    assert not verify_password("wrong-password", encoded)
    assert "Correct-Horse" not in encoded


def test_access_token_requires_expected_claims_and_signature() -> None:
    settings = get_settings()
    user_id = uuid.uuid4()
    family_id = uuid.uuid4()
    token, expires_in = create_access_token(
        user_id=user_id,
        family_id=family_id,
        settings=settings,
    )

    claims = decode_access_token(token, settings)
    assert claims["user_id"] == user_id
    assert claims["family_id"] == family_id
    assert claims["iss"] == settings.auth_jwt_issuer
    assert claims["aud"] == settings.auth_jwt_audience
    assert expires_in == settings.auth_access_token_minutes * 60

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(f"{token}corrupted", settings)


def test_refresh_and_api_key_formats_do_not_expose_stored_hashes() -> None:
    session_id = uuid.uuid4()
    refresh_token, refresh_hash = generate_refresh_token(session_id)
    parsed_id, refresh_secret = parse_refresh_token(refresh_token)
    api_key, prefix, key_hash = generate_api_key()
    parsed_prefix, key_secret = parse_api_key(api_key)

    assert parsed_id == session_id
    assert refresh_secret not in refresh_hash
    assert parsed_prefix == prefix
    assert key_secret not in key_hash
    assert api_key.startswith(f"aisoc_{prefix}_")


def test_role_permissions_are_fixed_and_least_privilege() -> None:
    assert permissions_for_role("viewer") == {Permission.SOC_READ}
    assert Permission.INVESTIGATIONS_CREATE in permissions_for_role("analyst")
    assert Permission.USERS_MANAGE not in permissions_for_role("analyst")
    assert permissions_for_role("admin") == frozenset(Permission)
    assert permissions_for_role("unknown") == frozenset()


def test_audit_sanitizer_removes_secrets_and_bounds_content() -> None:
    sanitized = sanitize_audit_details(
        {
            "password": "secret",
            "Authorization": "Bearer token",
            "raw_payload": {"sensitive": True},
            "safe": "x" * 1000,
            "nested": {"api_key": "hidden", "count": 2},
        }
    )

    assert "password" not in sanitized
    assert "Authorization" not in sanitized
    assert "raw_payload" not in sanitized
    assert "api_key" not in sanitized["nested"]
    assert sanitized["nested"]["count"] == 2
    assert len(sanitized["safe"]) == 512


@pytest.mark.anyio
async def test_login_rate_limiter_tracks_account_and_ip() -> None:
    redis = FakeRedis()
    limiter = LoginRateLimiter(redis, get_settings())
    email = "analyst@example.com"
    source_ip = "192.0.2.10"

    assert not await limiter.is_limited(email, source_ip)
    for _ in range(get_settings().auth_login_account_limit):
        await limiter.record_failure(email, source_ip)
    assert await limiter.is_limited(email, source_ip)
    assert all(
        seconds == get_settings().auth_login_window_seconds
        for seconds in redis.expirations.values()
    )
    await limiter.clear_account(email)
    assert not await limiter.is_limited(email, "192.0.2.11")
