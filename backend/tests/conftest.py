import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres:postgres@postgres:5432/ai_soc_test"
os.environ["REDIS_URL"] = "redis://redis:6379/1"
os.environ["SECRET_KEY"] = "test-secret"

import pytest
import pytest_asyncio
import psycopg
from sqlalchemy import delete

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.alert import Alert
from app.models.event import Event
from app.models.incident import Incident, IncidentAlert
from app.models.model_registry import ModelRegistry


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_test_database() -> None:
    with psycopg.connect("postgresql://postgres:postgres@postgres:5432/postgres", autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'ai_soc_test'")
            exists = cursor.fetchone()
            if not exists:
                cursor.execute("CREATE DATABASE ai_soc_test")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(autouse=True)
async def clear_detection_tables() -> None:
    async with SessionLocal() as session:
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
