import uuid
from datetime import UTC, datetime
import pytest

from app.db.session import SessionLocal
from app.models.auth import Role, User
from app.response.actions import ActionType, ProposedAction
from app.response.executor import InAppActionExecutor, TargetNotFoundError


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.ttls = {}

    async def set(self, key, value, ex=None):
        self.store[key] = value
        if ex:
            self.ttls[key] = ex

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        self.store.pop(key, None)
        self.ttls.pop(key, None)


@pytest.mark.asyncio
async def test_executor_block_ip_and_rollback():
    async with SessionLocal() as db_session:
        fake_redis = FakeRedis()
        executor = InAppActionExecutor(db_session, redis=fake_redis)

        action = ProposedAction(
            action_type=ActionType.BLOCK_IP,
            target="198.51.100.77",
            reason="Repeated brute force attack",
            evidence_refs=["alert:1"],
            confidence=0.95,
            ttl_seconds=7200,
        )

        # 1. Execute IP block
        res = await executor.execute(action)
        assert res.status == "executed"
        assert res.undo_available is True
        assert fake_redis.store.get("ai_soc:denylist:ip:198.51.100.77") == "blocked"
        assert fake_redis.ttls.get("ai_soc:denylist:ip:198.51.100.77") == 7200

        # 2. Rollback IP block
        rollback_res = await executor.rollback(res)
        assert rollback_res.status == "reverted"
        assert fake_redis.store.get("ai_soc:denylist:ip:198.51.100.77") is None


@pytest.mark.asyncio
async def test_executor_disable_user_and_rollback():
    async with SessionLocal() as db_session:
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="compromised@example.com",
            full_name="Compromised User",
            password_hash="fakehash",
            role_name="analyst",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()

        executor = InAppActionExecutor(db_session)

        action = ProposedAction(
            action_type=ActionType.DISABLE_USER,
            target="compromised@example.com",
            reason="Account takeover suspected",
            evidence_refs=["alert:2"],
            confidence=1.0,
        )

        # 1. Execute disable user
        res = await executor.execute(action)
        await db_session.commit()
        assert res.status == "executed"
        assert res.undo_available is True
        assert res.pre_state["is_active"] is True
        assert res.post_state["is_active"] is False

        user_db = await db_session.get(User, user_id)
        assert user_db.is_active is False

        # 2. Rollback
        rollback_res = await executor.rollback(res)
        await db_session.commit()
        assert rollback_res.status == "reverted"
        user_db = await db_session.get(User, user_id)
        assert user_db.is_active is True


@pytest.mark.asyncio
async def test_executor_revoke_sessions():
    async with SessionLocal() as db_session:
        user_id = uuid.uuid4()
        before_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        user = User(
            id=user_id,
            email="session_user@example.com",
            full_name="Session User",
            password_hash="fakehash",
            role_name="analyst",
            is_active=True,
            credentials_changed_at=before_time,
        )
        db_session.add(user)
        await db_session.commit()

        executor = InAppActionExecutor(db_session)

        action = ProposedAction(
            action_type=ActionType.REVOKE_SESSIONS,
            target=str(user_id),
            reason="Revoke token family after credential leak",
            evidence_refs=["alert:3"],
            confidence=0.9,
        )

        res = await executor.execute(action)
        await db_session.commit()
        assert res.status == "executed"
        assert res.undo_available is False  # Cannot un-revoke sessions

        user_db = await db_session.get(User, user_id)
        assert user_db.credentials_changed_at > before_time

