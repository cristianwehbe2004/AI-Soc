from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.redis import redis_client
from app.models.auth import AuditLog
from app.models.response_action import ResponseAction
from app.realtime.events import RealtimePublisher
from app.repositories.auth_repository import AuthSessionRepository, UserRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.event_repository import EventRepository
from app.schemas.response_action import ResponseActionCreate, ResponseActionResponse

QUEUE_KEY = "ai_soc:response_actions"


class ResponseActionError(ValueError):
    pass


class ResponseActionService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def list_for_incident(self, incident_id: uuid.UUID) -> list[ResponseActionResponse]:
        rows = await self.session.scalars(
            select(ResponseAction).where(ResponseAction.incident_id == incident_id).order_by(ResponseAction.created_at.desc())
        )
        return [ResponseActionResponse.model_validate(row) for row in rows]

    async def propose(self, incident_id: uuid.UUID, payload: ResponseActionCreate, actor_id: uuid.UUID) -> ResponseActionResponse:
        incident = await IncidentRepository(self.session).get(incident_id)
        if incident is None:
            raise ResponseActionError("Incident not found")
        existing = await self.session.scalar(select(ResponseAction).where(
            ResponseAction.incident_id == incident_id,
            ResponseAction.idempotency_key == payload.idempotency_key,
        ))
        if existing:
            if existing.action_type != payload.action_type or existing.target != payload.target:
                raise ResponseActionError("Idempotency key is already used for another action")
            return ResponseActionResponse.model_validate(existing)
        alerts = await IncidentRepository(self.session).get_alerts_for_incident(incident_id)
        events = await EventRepository(self.session).get_by_ids([alert.event_id for alert in alerts])
        valid = {f"incident:{incident_id}"}
        valid.update(f"alert:{alert.id}" for alert in alerts)
        valid.update(f"event:{event.event_id}" for event in events.values())
        if set(payload.evidence_refs) - valid:
            raise ResponseActionError("Action cites evidence outside this incident")
        if payload.action_type == "revoke_app_sessions" and await UserRepository(self.session).get(uuid.UUID(payload.target)) is None:
            raise ResponseActionError("Target app user not found")
        action = ResponseAction(
            incident_id=incident_id,
            proposed_by=actor_id,
            **payload.model_dump(),
        )
        self.session.add(action)
        await self.session.flush()
        return ResponseActionResponse.model_validate(action)

    async def decide(self, action_id: uuid.UUID, actor_id: uuid.UUID, *, approve: bool) -> ResponseActionResponse:
        action = await self.session.scalar(select(ResponseAction).where(ResponseAction.id == action_id).with_for_update())
        if action is None:
            raise ResponseActionError("Response action not found")
        if action.status != "proposed":
            raise ResponseActionError("Response action has already been decided")
        if action.proposed_by == actor_id:
            raise ResponseActionError("Proposer cannot approve their own action")
        if approve and action.action_type != "revoke_app_sessions" and not self.settings.aws_response_enabled:
            raise ResponseActionError("AWS response is disabled")
        action.status = "approved" if approve else "rejected"
        action.approved_by = actor_id
        action.updated_at = datetime.now(UTC)
        await self.session.flush()
        return ResponseActionResponse.model_validate(action)


async def publish_action(action: ResponseActionResponse, settings: Settings) -> None:
    await RealtimePublisher(redis_client, channel_prefix=settings.realtime_redis_channel_prefix).publish(
        f"response.{action.status}",
        entity_id=str(action.id),
        payload={"incident_id": str(action.incident_id), "status": action.status, "action_type": action.action_type},
        version=int(action.updated_at.timestamp() * 1_000_000),
    )


async def execute_action(action_id: uuid.UUID, session_factory, settings: Settings) -> None:
    async with session_factory() as session:
        result = await session.execute(
            update(ResponseAction)
            .where(ResponseAction.id == action_id, ResponseAction.status == "approved")
            .values(status="running", updated_at=datetime.now(UTC))
            .returning(ResponseAction)
        )
        action = result.scalar_one_or_none()
        if action is None:
            await session.rollback()
            return
        await session.commit()
        try:
            await publish_action(ResponseActionResponse.model_validate(action), settings)
        except Exception:
            pass
        try:
            if action.action_type == "revoke_app_sessions":
                user_id = uuid.UUID(action.target)
                if await UserRepository(session).get(user_id) is None:
                    raise ResponseActionError("Target app user no longer exists")
                await AuthSessionRepository(session).revoke_user(user_id)
                outcome = {"verified": True, "user_id": str(user_id)}
            else:
                outcome = await asyncio.to_thread(_execute_aws_action, action, settings)
            action.status = "succeeded"
            action.result = outcome
            action.error = None
        except Exception as exc:
            await session.rollback()
            action = await session.get(ResponseAction, action_id)
            action.status = "failed"
            action.error = str(exc)[:1000]
        action.updated_at = datetime.now(UTC)
        session.add(AuditLog(
            actor_type="system", actor_id=action.approved_by,
            actor_label="response_worker", action="response.execute",
            resource_type="response_action", resource_id=str(action.id),
            outcome=action.status, details={"action_type": action.action_type, "target": action.target},
        ))
        await session.commit()
        try:
            await publish_action(ResponseActionResponse.model_validate(action), settings)
        except Exception:
            pass


def _execute_aws_action(action: ResponseAction, settings: Settings) -> dict:
    if not settings.aws_response_enabled:
        raise ResponseActionError("AWS response is disabled")
    allowed = {item.strip() for item in settings.aws_allowed_account_ids.split(",") if item.strip()}
    if not allowed or action.account_id not in allowed:
        raise ResponseActionError("AWS account is not allowlisted")
    import boto3

    session = boto3.Session()
    identity = session.client("sts").get_caller_identity()
    if identity["Account"] != action.account_id:
        raise ResponseActionError("AWS credentials target a different account")
    if action.action_type == "disable_aws_access_key":
        try:
            username, key_id = action.target.split(":", 1)
        except ValueError as exc:
            raise ResponseActionError("Target must be username:access_key_id") from exc
        if not username or not key_id.startswith("AKIA") or len(key_id) != 20:
            raise ResponseActionError("Target must identify a long-term IAM user access key")
        client = session.client("iam")
        keys = client.list_access_keys(UserName=username)["AccessKeyMetadata"]
        if not any(item["AccessKeyId"] == key_id for item in keys):
            raise ResponseActionError("IAM access key is no longer attached to target user")
        response = client.update_access_key(UserName=username, AccessKeyId=key_id, Status="Inactive")
        verified = client.list_access_keys(UserName=username)["AccessKeyMetadata"]
        if not any(item["AccessKeyId"] == key_id and item["Status"] == "Inactive" for item in verified):
            raise ResponseActionError("IAM access key deactivation could not be verified")
        return {"verified": True, "aws_request_id": response["ResponseMetadata"]["RequestId"]}
    if action.action_type == "block_s3_public_access":
        if not settings.aws_allowed_bucket_prefix or not action.target.startswith(settings.aws_allowed_bucket_prefix):
            raise ResponseActionError("S3 bucket is not allowlisted")
        client = session.client("s3")
        client.head_bucket(Bucket=action.target, ExpectedBucketOwner=action.account_id)
        config = {key: True for key in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")}
        response = client.put_public_access_block(Bucket=action.target, PublicAccessBlockConfiguration=config, ExpectedBucketOwner=action.account_id)
        current = client.get_public_access_block(Bucket=action.target, ExpectedBucketOwner=action.account_id)["PublicAccessBlockConfiguration"]
        if not all(current.get(key) is True for key in config):
            raise ResponseActionError("S3 public access block could not be verified")
        return {"verified": True, "aws_request_id": response["ResponseMetadata"]["RequestId"]}
    raise ResponseActionError("Unsupported action type")
