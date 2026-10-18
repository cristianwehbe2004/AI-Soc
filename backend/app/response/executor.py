from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.auth import AuditLog, User
from app.repositories.auth_repository import AuthSessionRepository, UserRepository
from app.response.actions import ActionType, ProposedAction
from app.response.audit_chain import compute_entry_hash


class ExecutionError(RuntimeError):
    pass


class TargetNotFoundError(ExecutionError):
    pass


@dataclass
class ExecutionResult:
    action_id: str
    action_type: ActionType
    target: str
    status: str  # "executed", "reverted", "failed"
    pre_state: dict[str, Any]
    post_state: dict[str, Any]
    undo_available: bool
    executed_at: datetime
    error: str | None = None


class InAppActionExecutor:
    """
    Executes in-app containment actions with strict state capture,
    reversible rollbacks (undo), and automatic TTL expiration.
    Operates independently with no LLM in the execution path.
    """

    def __init__(
        self,
        session: AsyncSession,
        redis: Any | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.settings = settings
        self.user_repo = UserRepository(session)
        self.auth_session_repo = AuthSessionRepository(session)

    async def execute(self, action: ProposedAction, *, actor_label: str = "autonomous_executor") -> ExecutionResult:
        """Executes the action and captures exact pre-state for full reversibility."""
        action_id = str(uuid.uuid4())
        executed_at = datetime.now(UTC)

        try:
            if action.action_type == ActionType.REVOKE_SESSIONS:
                result = await self._execute_revoke_sessions(action, action_id, executed_at)
            elif action.action_type == ActionType.DISABLE_USER:
                result = await self._execute_disable_user(action, action_id, executed_at)
            elif action.action_type == ActionType.BLOCK_IP:
                result = await self._execute_block_ip(action, action_id, executed_at)
            else:
                raise ExecutionError(f"Unsupported in-app action type: {action.action_type}")

            await self._record_audit(
                action_id=action_id,
                action_type=action.action_type,
                target=action.target,
                outcome="succeeded",
                actor_label=actor_label,
                details={"pre_state": result.pre_state, "post_state": result.post_state},
            )
            return result

        except Exception as exc:
            await self._record_audit(
                action_id=action_id,
                action_type=action.action_type,
                target=action.target,
                outcome="failed",
                actor_label=actor_label,
                details={"error": str(exc)},
            )
            raise

    async def rollback(self, execution_result: ExecutionResult, *, actor_label: str = "analyst_rollback") -> ExecutionResult:
        """Rolls back an executed action using stored pre-state."""
        if not execution_result.undo_available:
            raise ExecutionError(f"Action {execution_result.action_type} does not support rollback")

        reverted_at = datetime.now(UTC)
        action_type = execution_result.action_type
        target = execution_result.target
        pre_state = execution_result.pre_state

        if action_type == ActionType.DISABLE_USER:
            user = await self._find_user(target)
            if user is None:
                raise TargetNotFoundError(f"User '{target}' no longer exists")
            user.is_active = pre_state["is_active"]
            await self.session.flush()

        elif action_type == ActionType.BLOCK_IP:
            if self.redis is not None:
                await self.redis.delete(f"ai_soc:denylist:ip:{target}")

        elif action_type == ActionType.REVOKE_SESSIONS:
            # Note: Revoked JWT/refresh sessions cannot and should NOT be restored
            # because the credentials were compromised; rollback requires issuance of a new credential.
            raise ExecutionError("Revoked sessions cannot be un-revoked for security safety")

        await self._record_audit(
            action_id=execution_result.action_id,
            action_type=f"rollback.{action_type}",
            target=target,
            outcome="reverted",
            actor_label=actor_label,
            details={"restored_to": pre_state},
        )

        return ExecutionResult(
            action_id=execution_result.action_id,
            action_type=action_type,
            target=target,
            status="reverted",
            pre_state=execution_result.post_state,
            post_state=pre_state,
            undo_available=False,
            executed_at=reverted_at,
        )

    # --- Internal Implementation ---

    async def _execute_revoke_sessions(
        self, action: ProposedAction, action_id: str, executed_at: datetime
    ) -> ExecutionResult:
        user = await self._find_user(action.target)
        if user is None:
            raise TargetNotFoundError(f"Target user '{action.target}' not found")

        # Capture pre-state
        pre_state = {
            "user_id": str(user.id),
            "email": user.email,
            "credentials_changed_at": user.credentials_changed_at.isoformat(),
        }

        # 1. Invalidate all active session tokens in PostgreSQL
        await self.auth_session_repo.revoke_user(user.id)

        # 2. Bump credentials_changed_at so existing short-lived access JWTs are immediately rejected by get_current_user
        user.credentials_changed_at = executed_at
        await self.session.flush()

        return ExecutionResult(
            action_id=action_id,
            action_type=action.action_type,
            target=action.target,
            status="executed",
            pre_state=pre_state,
            post_state={"credentials_changed_at": executed_at.isoformat(), "sessions_revoked": True},
            undo_available=False,  # Security rule: never restore compromised token sessions
            executed_at=executed_at,
        )

    async def _execute_disable_user(
        self, action: ProposedAction, action_id: str, executed_at: datetime
    ) -> ExecutionResult:
        user = await self._find_user(action.target)
        if user is None:
            raise TargetNotFoundError(f"Target user '{action.target}' not found")

        pre_state = {
            "user_id": str(user.id),
            "email": user.email,
            "is_active": user.is_active,
        }

        # Disable user
        user.is_active = False

        # Also immediately invalidate their active sessions
        await self.auth_session_repo.revoke_user(user.id)
        user.credentials_changed_at = executed_at
        await self.session.flush()

        return ExecutionResult(
            action_id=action_id,
            action_type=action.action_type,
            target=action.target,
            status="executed",
            pre_state=pre_state,
            post_state={"is_active": False, "sessions_revoked": True},
            undo_available=True,
            executed_at=executed_at,
        )

    async def _execute_block_ip(
        self, action: ProposedAction, action_id: str, executed_at: datetime
    ) -> ExecutionResult:
        target_ip = action.target.strip()
        ttl = action.ttl_seconds or 86400  # Default 24 hour TTL

        pre_state = {"blocked": False, "ip": target_ip}

        if self.redis is not None:
            key = f"ai_soc:denylist:ip:{target_ip}"
            await self.redis.set(key, "blocked", ex=ttl)

        return ExecutionResult(
            action_id=action_id,
            action_type=action.action_type,
            target=target_ip,
            status="executed",
            pre_state=pre_state,
            post_state={"blocked": True, "ttl_seconds": ttl},
            undo_available=True,
            executed_at=executed_at,
        )

    async def _find_user(self, target: str) -> User | None:
        try:
            user_uuid = uuid.UUID(target)
            user = await self.user_repo.get(user_uuid)
            if user:
                return user
        except ValueError:
            pass
        return await self.user_repo.get_by_email(target)

    async def _record_audit(
        self,
        *,
        action_id: str,
        action_type: str,
        target: str,
        outcome: str,
        actor_label: str,
        details: dict[str, Any],
    ) -> None:
        log = AuditLog(
            actor_type="system",
            actor_label=actor_label,
            action=f"autonomous_response.{action_type}",
            resource_type="response_action",
            resource_id=action_id,
            outcome=outcome,
            details={"target": target, **details},
        )
        self.session.add(log)
        await self.session.flush()
