from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import IncidentNote


class IncidentNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_incident(self, incident_id: uuid.UUID) -> list[IncidentNote]:
        result = await self.session.execute(
            select(IncidentNote)
            .where(IncidentNote.incident_id == incident_id)
            .order_by(IncidentNote.created_at.asc())
        )
        return list(result.scalars().all())

    async def get(self, note_id: uuid.UUID) -> IncidentNote | None:
        return await self.session.get(IncidentNote, note_id)

    async def create(self, note: IncidentNote) -> IncidentNote:
        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note)
        return note

    async def update(self, note: IncidentNote, content: str) -> IncidentNote:
        note.content = content
        await self.session.flush()
        await self.session.refresh(note)
        return note