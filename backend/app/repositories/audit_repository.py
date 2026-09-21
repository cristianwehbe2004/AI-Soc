from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, audit_log: AuditLog) -> AuditLog:
        self.session.add(audit_log)
        await self.session.flush()
        return audit_log

    async def list(
        self,
        *,
        actor_type: str | None,
        actor_id: uuid.UUID | None,
        action: str | None,
        outcome: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AuditLog], int]:
        query = self._filters(
            select(AuditLog), actor_type, actor_id, action, outcome, start_time, end_time
        ).order_by(AuditLog.created_at.desc())
        count_query = self._filters(
            select(func.count()).select_from(AuditLog),
            actor_type,
            actor_id,
            action,
            outcome,
            start_time,
            end_time,
        )
        rows = await self.session.execute(query.limit(limit).offset(offset))
        count = await self.session.scalar(count_query)
        return list(rows.scalars()), int(count or 0)

    @staticmethod
    def _filters(
        query: Select,
        actor_type: str | None,
        actor_id: uuid.UUID | None,
        action: str | None,
        outcome: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> Select:
        if actor_type:
            query = query.where(AuditLog.actor_type == actor_type)
        if actor_id:
            query = query.where(AuditLog.actor_id == actor_id)
        if action:
            query = query.where(AuditLog.action == action)
        if outcome:
            query = query.where(AuditLog.outcome == outcome)
        if start_time:
            query = query.where(AuditLog.created_at >= start_time)
        if end_time:
            query = query.where(AuditLog.created_at <= end_time)
        return query
