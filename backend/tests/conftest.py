import os

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
os.environ["SECRET_KEY"] = "test-secret"
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
from app.db.session import SessionLocal, engine
from app.core.config import get_settings
from app.models.alert import Alert
from app.models.event import Event
from app.models.incident import Incident, IncidentAlert
from app.models.investigation import Investigation
from app.models.model_registry import ModelRegistry
from app.repositories.mitre_repository import MitreRepository


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
        await cleanup_redis.delete(settings.investigation_queue_key)
    finally:
        await cleanup_redis.aclose()
    async with SessionLocal() as session:
        await session.execute(delete(Investigation))
        await session.execute(delete(IncidentAlert))
        await session.execute(delete(Incident))
        await session.execute(delete(Alert))
        await session.execute(delete(Event))
        await session.execute(delete(ModelRegistry))
        await session.commit()
    yield


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
