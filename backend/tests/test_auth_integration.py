from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.session import SessionLocal
from app.models.auth import AuditLog, AuthSession, ServiceApiKey, User
from app.services.bootstrap_service import create_first_admin
from sqlalchemy import select
from conftest import AUTH_HEADERS, TEST_PASSWORD


async def login(client: AsyncClient, email: str, password: str = TEST_PASSWORD):
    return await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )


def sample_event(event_id: str | None = None) -> dict:
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "source": "auth-test",
        "source_type": "application",
        "event_type": "api_request",
        "category": "api",
        "event_id": event_id or f"auth-test-{uuid.uuid4()}",
        "status": "success",
        "raw_payload": {"password": "must-not-enter-audit"},
    }


@pytest.mark.anyio
async def test_login_refresh_logout_and_me_flow() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_response = await login(client, "VIEWER@example.com")
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        assert login_response.json()["expires_in"] == 900
        assert "ai_soc_refresh" in client.cookies

        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["role_name"] == "viewer"

        old_refresh = client.cookies["ai_soc_refresh"]
        refresh_response = await client.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 200
        assert client.cookies["ai_soc_refresh"] != old_refresh

        logout_response = await client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200
        revoked_access = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_response.json()['access_token']}"},
        )
        assert revoked_access.status_code == 401


@pytest.mark.anyio
async def test_refresh_reuse_revokes_the_session_family() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await login(client, "analyst@example.com")).status_code == 200
        original = client.cookies["ai_soc_refresh"]
        assert (await client.post("/api/v1/auth/refresh")).status_code == 200
        replacement = client.cookies["ai_soc_refresh"]

        client.cookies.set("ai_soc_refresh", original)
        replay = await client.post("/api/v1/auth/refresh")
        assert replay.status_code == 401
        client.cookies.set("ai_soc_refresh", replacement)
        family_revoked = await client.post("/api/v1/auth/refresh")
        assert family_revoked.status_code == 401


@pytest.mark.anyio
async def test_concurrent_refresh_allows_one_rotation_then_revokes_family() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as login_client:
        assert (await login(login_client, "analyst@example.com")).status_code == 200
        original = login_client.cookies["ai_soc_refresh"]

    async with (
        AsyncClient(transport=transport, base_url="http://testserver") as first,
        AsyncClient(transport=transport, base_url="http://testserver") as second,
    ):
        first.cookies.set("ai_soc_refresh", original)
        second.cookies.set("ai_soc_refresh", original)
        responses = await asyncio.gather(
            first.post("/api/v1/auth/refresh"),
            second.post("/api/v1/auth/refresh"),
        )
        assert sorted(response.status_code for response in responses) == [200, 401]
        winner = first if responses[0].status_code == 200 else second
        assert (await winner.post("/api/v1/auth/refresh")).status_code == 401


@pytest.mark.anyio
async def test_login_rate_limit_uses_generic_errors() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        failures = [
            await login(client, "viewer@example.com", "incorrect-password")
            for _ in range(5)
        ]
        limited = await login(client, "viewer@example.com", "incorrect-password")

    assert all(response.status_code == 401 for response in failures)
    assert {response.json()["detail"] for response in failures} == {
        "Invalid email or password"
    }
    assert limited.status_code == 429


@pytest.mark.anyio
async def test_admin_user_lifecycle_and_immediate_deactivation() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/v1/users",
            headers=AUTH_HEADERS["admin"],
            json={
                "email": "new.analyst@example.com",
                "full_name": "New Analyst",
                "password": "New-Analyst-Password-1",
                "role_name": "analyst",
            },
        )
        assert created.status_code == 201
        user_id = created.json()["id"]
        listed = await client.get("/api/v1/users", headers=AUTH_HEADERS["admin"])
        assert listed.status_code == 200
        assert any(item["id"] == user_id for item in listed.json()["items"])

        changed_role = await client.patch(
            f"/api/v1/users/{user_id}",
            headers=AUTH_HEADERS["admin"],
            json={"role_name": "viewer"},
        )
        assert changed_role.status_code == 200
        assert changed_role.json()["role_name"] == "viewer"

        viewer_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "ai-soc-test-viewer"))
        deactivated = await client.patch(
            f"/api/v1/users/{viewer_id}",
            headers=AUTH_HEADERS["admin"],
            json={"is_active": False},
        )
        assert deactivated.status_code == 200
        denied = await client.get("/api/v1/events", headers=AUTH_HEADERS["viewer"])
        assert denied.status_code == 401


@pytest.mark.anyio
async def test_permission_matrix_and_scoped_ingestion() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.get("/api/v1/events")).status_code == 401
        assert (
            await client.get("/api/v1/events", headers=AUTH_HEADERS["viewer"])
        ).status_code == 200
        assert (
            await client.post(
                f"/api/v1/incidents/{uuid.uuid4()}/investigations",
                headers=AUTH_HEADERS["viewer"],
            )
        ).status_code == 403
        assert (
            await client.get("/api/v1/users", headers=AUTH_HEADERS["analyst"])
        ).status_code == 403
        assert (
            await client.get("/api/v1/audit-logs", headers=AUTH_HEADERS["admin"])
        ).status_code == 200
        assert (
            await client.get("/api/v1/events", headers=AUTH_HEADERS["api_key"])
        ).status_code == 401
        assert (
            await client.post(
                f"/api/v1/incidents/{uuid.uuid4()}/investigations",
                headers=AUTH_HEADERS["api_key"],
            )
        ).status_code == 401
        assert (
            await client.post(
                "/api/v1/events",
                headers=AUTH_HEADERS["api_key"],
                json=sample_event(),
            )
        ).status_code == 201


@pytest.mark.anyio
async def test_api_key_lifecycle_and_audit_redaction() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/v1/api-keys",
            headers=AUTH_HEADERS["admin"],
            json={"name": "secondary-simulator", "scopes": ["events:write"]},
        )
        assert created.status_code == 201
        raw_key = created.json()["api_key"]
        key_id = created.json()["id"]

        listed = await client.get("/api/v1/api-keys", headers=AUTH_HEADERS["admin"])
        assert listed.status_code == 200
        assert all("api_key" not in item for item in listed.json()["items"])

        ingested = await client.post(
            "/api/v1/events",
            headers={"X-API-Key": raw_key},
            json=sample_event("audit-redaction-event"),
        )
        assert ingested.status_code == 201
        revoked = await client.post(
            f"/api/v1/api-keys/{key_id}/revoke",
            headers=AUTH_HEADERS["admin"],
        )
        assert revoked.status_code == 200
        denied = await client.post(
            "/api/v1/events",
            headers={"X-API-Key": raw_key},
            json=sample_event(),
        )
        assert denied.status_code == 401

        audit = await client.get(
            "/api/v1/audit-logs",
            headers=AUTH_HEADERS["admin"],
            params={"action": "events.ingest"},
        )
        assert audit.status_code == 200
        assert audit.json()["total"] == 1
        serialized = str(audit.json())
        assert raw_key not in serialized
        assert "must-not-enter-audit" not in serialized


@pytest.mark.anyio
async def test_password_change_revokes_every_session() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await login(client, "viewer@example.com")
        token = first.json()["access_token"]
        changed = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": TEST_PASSWORD,
                "new_password": "Updated-Correct-Password-2",
            },
        )
        assert changed.status_code == 200
        assert (
            await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        ).status_code == 401
        assert (await login(client, "viewer@example.com", TEST_PASSWORD)).status_code == 401
        assert (
            await login(client, "viewer@example.com", "Updated-Correct-Password-2")
        ).status_code == 200


@pytest.mark.anyio
async def test_only_hashes_are_persisted_for_sessions_and_service_keys() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await login(client, "admin@example.com")
        refresh_token = client.cookies["ai_soc_refresh"]
        created = await client.post(
            "/api/v1/api-keys",
            headers={"Authorization": f"Bearer {response.json()['access_token']}"},
            json={"name": "hash-check"},
        )
        raw_key = created.json()["api_key"]

    async with SessionLocal() as session:
        auth_session = (
            await session.execute(select(AuthSession).order_by(AuthSession.created_at.desc()))
        ).scalars().first()
        service_key = (
            await session.execute(
                select(ServiceApiKey).where(
                    ServiceApiKey.id == uuid.UUID(created.json()["id"])
                )
            )
        ).scalar_one()
        assert refresh_token not in auth_session.token_hash
        assert raw_key not in service_key.key_hash
        assert len(auth_session.token_hash) == 64
        assert len(service_key.key_hash) == 64

        logs = list((await session.execute(select(AuditLog))).scalars())
        assert logs
        assert raw_key not in str([log.details for log in logs])


@pytest.mark.anyio
async def test_first_admin_bootstrap_is_idempotent() -> None:
    async with SessionLocal() as session:
        created = await create_first_admin(
            session,
            email="Bootstrap.Admin@Example.com",
            full_name="Bootstrap Admin",
            password="Bootstrap-Password-123",
        )
        repeated = await create_first_admin(
            session,
            email="bootstrap.admin@example.com",
            full_name="Bootstrap Admin",
            password="Different-Password-456",
        )

    assert created
    assert not repeated
    async with SessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.email == "bootstrap.admin@example.com")
            )
        ).scalar_one()
        assert user.role_name == "admin"
        assert user.is_active


@pytest.mark.anyio
async def test_cors_allows_only_configured_frontend_origin() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        allowed = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        denied = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert "access-control-allow-origin" not in denied.headers
