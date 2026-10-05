from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.redis import redis_client
from app.db.session import get_db_session
from app.models.auth import User
from app.repositories.audit_repository import AuditRepository
from app.schemas.response_action import ResponseActionCreate, ResponseActionResponse
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.services.audit_service import AuditService
from app.services.response_actions import QUEUE_KEY, ResponseActionError, ResponseActionService, publish_action

router = APIRouter(tags=["response-actions"])
Reader = Annotated[User, Depends(require_permission(Permission.SOC_READ))]
Proposer = Annotated[User, Depends(require_permission(Permission.RESPONSES_PROPOSE))]
Approver = Annotated[User, Depends(require_permission(Permission.RESPONSES_APPROVE))]


@router.get("/incidents/{incident_id}/response-actions", response_model=list[ResponseActionResponse])
async def list_actions(incident_id: uuid.UUID, actor: Reader, session: AsyncSession = Depends(get_db_session)):
    return await ResponseActionService(session, get_settings()).list_for_incident(incident_id)


@router.post("/incidents/{incident_id}/response-actions", response_model=ResponseActionResponse, status_code=201)
async def propose_action(
    incident_id: uuid.UUID, payload: ResponseActionCreate, request: Request, actor: Proposer,
    session: AsyncSession = Depends(get_db_session),
):
    try:
        action = await ResponseActionService(session, get_settings()).propose(incident_id, payload, actor.id)
    except ResponseActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await AuditService(AuditRepository(session)).record(
        request=request, action="response.propose", outcome="success", actor_type="user",
        actor_id=actor.id, actor_label=actor.email,
        resource_type="response_action", resource_id=str(action.id),
        details={"action_type": action.action_type, "incident_id": str(incident_id)},
    )
    await session.commit()
    try:
        await publish_action(action, get_settings())
    except Exception:
        pass
    return action


@router.get("/response-actions/{action_id}", response_model=ResponseActionResponse)
async def get_action(action_id: uuid.UUID, actor: Reader, session: AsyncSession = Depends(get_db_session)):
    from app.models.response_action import ResponseAction
    action = await session.get(ResponseAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Response action not found")
    return ResponseActionResponse.model_validate(action)


@router.post("/response-actions/{action_id}/{decision}", response_model=ResponseActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def decide_action(
    action_id: uuid.UUID, decision: str, request: Request, actor: Approver,
    session: AsyncSession = Depends(get_db_session),
):
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=404, detail="Unknown decision")
    try:
        action = await ResponseActionService(session, get_settings()).decide(action_id, actor.id, approve=decision == "approve")
    except ResponseActionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await AuditService(AuditRepository(session)).record(
        request=request, action=f"response.{decision}", outcome="success", actor_type="user",
        actor_id=actor.id, actor_label=actor.email,
        resource_type="response_action", resource_id=str(action.id),
        details={"action_type": action.action_type},
    )
    await session.commit()
    if decision == "approve":
        await redis_client.rpush(QUEUE_KEY, str(action.id))
    try:
        await publish_action(action, get_settings())
    except Exception:
        pass
    return action
