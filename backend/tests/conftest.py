import os
import uuid
from datetime import UTC, datetime, timedelta

test_database_url = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@postgres:5432/ai_soc_test",
)
test_database_name = test_database_url.rsplit("/", 1)[-1]
admin_database_url = (
    test_database_url.replace("postgresql+psycopg://", "postgresql://").rsplit("/", 1)[0]
    + "/postgres"
)

os.environ["DATABASE_URL"] = test_database_url
os.environ["REDIS_URL"] = os.getenv("TEST_REDIS_URL", "redis://redis:6379/1")
os.environ["SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
os.environ["APP_ENV"] = "test"
os.environ["LLM_ENABLED"] = "true"
os.environ["LLM_PROVIDER"] = "openai"
os.environ["LLM_API_KEY"] = "test-key"
os.environ["LLM_MODEL"] = "mock-investigator"

import pytest
import pytest_asyncio
import psycopg
from redis.asyncio import Redis
from psycopg import sql
from sqlalchemy import delete

from app.db.base import Base
from app.db.redis import redis_client
from app.db.session import SessionLocal, engine
from app.core.config import get_settings
from app.models.alert import Alert
from app.models.auth import AuditLog, AuthSession, Role, ServiceApiKey, User
from app.models.event import Event
from app.models.incident import Incident, IncidentAlert
from app.models.investigation import Investigation
from app.models.model_registry import ModelRegistry
from app.repositories.mitre_repository import MitreRepository
from app.security.passwords import hash_password
from app.security.tokens import create_access_token, hash_secret

TEST_PASSWORD = "Correct-Horse-Battery-1"
TEST_API_KEY = "aisoc_testkey_test-service-secret-value"
AUTH_HEADERS: dict[str, dict[str, str]] = {}


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_test_database() -> None:
    with psycopg.connect(admin_database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (test_database_name,))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_database_name)))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        for name, description in (
            ("admin", "Full platform administration"),
            ("analyst", "SOC analysis and investigation"),
            ("viewer", "Read-only SOC access"),
        ):
            if await session.get(Role, name) is None:
                session.add(Role(name=name, description=description))
        await MitreRepository(session).seed_core_catalog()
        await session.commit()
    yield


@pytest_asyncio.fixture(autouse=True)
async def clear_detection_tables() -> None:
    settings = get_settings()
    cleanup_redis = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        await cleanup_redis.flushdb()
    finally:
        await cleanup_redis.aclose()
    async with SessionLocal() as session:
        await session.execute(delete(AuditLog))
        await session.execute(delete(AuthSession))
        await session.execute(delete(ServiceApiKey))
        await session.execute(delete(Investigation))
        await session.execute(delete(IncidentAlert))
        await session.execute(delete(Incident))
        await session.execute(delete(Alert))
        await session.execute(delete(Event))
        await session.execute(delete(ModelRegistry))
        await session.execute(delete(User))
        users = {}
        for role in ("admin", "analyst", "viewer"):
            user = User(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, f"ai-soc-test-{role}"),
                email=f"{role}@example.com",
                full_name=f"Test {role.title()}",
                password_hash=hash_password(TEST_PASSWORD),
                role_name=role,
                is_active=True,
            )
            session.add(user)
            users[role] = user
        await session.flush()
        AUTH_HEADERS.clear()
        for role, user in users.items():
            family_id = uuid.uuid4()
            session.add(
                AuthSession(
                    family_id=family_id,
                    user_id=user.id,
                    token_hash=hash_secret(f"fixture-{role}-{uuid.uuid4()}"),
                    expires_at=datetime.now(UTC) + timedelta(days=1),
                )
            )
            access_token, _ = create_access_token(
                user_id=user.id,
                family_id=family_id,
                settings=settings,
            )
            AUTH_HEADERS[role] = {"Authorization": f"Bearer {access_token}"}
        service_key = ServiceApiKey(
            name="test-simulator",
            prefix="testkey",
            key_hash=hash_secret("test-service-secret-value"),
            scopes=["events:write"],
            created_by=users["admin"].id,
        )
        session.add(service_key)
        AUTH_HEADERS["api_key"] = {"X-API-Key": TEST_API_KEY}
        await session.commit()
    yield
    await redis_client.aclose()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
