from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation import Investigation


class InvestigationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, investigation: Investigation) -> Investigation:
        self.session.add(investigation)
        await self.session.flush()
        await self.session.refresh(investigation)
        return investigation

    async def get(self, investigation_id: uuid.UUID) -> Investigation | None:
        return await self.session.get(Investigation, investigation_id)

    async def find_for_context(
        self,
        *,
        incident_id: uuid.UUID,
        context_hash: str,
        prompt_version: str,
    ) -> Investigation | None:
        result = await self.session.execute(
            select(Investigation).where(
                Investigation.incident_id == incident_id,
                Investigation.context_hash == context_hash,
                Investigation.prompt_version == prompt_version,
            )
        )
        return result.scalar_one_or_none()

    async def acquire_context_lock(self, lock_key: str) -> None:
        await self.session.execute(
            select(
                func.pg_advisory_xact_lock(
                    func.hashtextextended(lock_key, 0)
                )
            )
        )

    async def list_for_incident(
        self,
        incident_id: uuid.UUID,
    ) -> list[Investigation]:
        result = await self.session.execute(
            select(Investigation)
            .where(Investigation.incident_id == incident_id)
            .order_by(Investigation.created_at.desc())
        )
        return list(result.scalars().all())

    async def claim(self, investigation_id: uuid.UUID) -> Investigation | None:
        now = datetime.now(UTC)
        result = await self.session.execute(
            update(Investigation)
            .where(
                Investigation.id == investigation_id,
                Investigation.status == "queued",
            )
            .values(
                status="running",
                started_at=now,
                completed_at=None,
                error=None,
                attempt_count=Investigation.attempt_count + 1,
                updated_at=now,
            )
            .returning(Investigation)
        )
        return result.scalar_one_or_none()

    async def requeue(self, investigation: Investigation) -> Investigation:
        now = datetime.now(UTC)
        investigation.status = "queued"
        investigation.queued_at = now
        investigation.started_at = None
        investigation.completed_at = None
        investigation.error = None
        investigation.validation_errors = []
        investigation.updated_at = now
        await self.session.flush()
        return investigation

    async def checkpoint_context(
        self,
        investigation: Investigation,
        context_snapshot: dict,
    ) -> Investigation:
        investigation.context_snapshot = context_snapshot
        investigation.updated_at = datetime.now(UTC)
        await self.session.flush()
        return investigation

    async def complete(
        self,
        investigation: Investigation,
        *,
        context_snapshot: dict,
        result: dict,
        provider_response_ids: list[str],
        input_tokens: int,
        output_tokens: int,
    ) -> Investigation:
        now = datetime.now(UTC)
        investigation.status = "completed"
        investigation.context_snapshot = context_snapshot
        investigation.result = result
        investigation.provider_response_ids = provider_response_ids
        investigation.input_tokens = input_tokens
        investigation.output_tokens = output_tokens
        investigation.validation_errors = []
        investigation.error = None
        investigation.completed_at = now
        investigation.updated_at = now
        await self.session.flush()
        return investigation

    async def fail(
        self,
        investigation: Investigation,
        *,
        error: str,
        validation_errors: list[str] | None = None,
    ) -> Investigation:
        now = datetime.now(UTC)
        investigation.status = "failed"
        investigation.error = error[:4000]
        investigation.validation_errors = validation_errors or []
        investigation.completed_at = now
        investigation.updated_at = now
        await self.session.flush()
        return investigation
