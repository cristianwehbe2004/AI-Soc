from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.ml.inference import MLInferenceService
from app.models.auth import User
from app.models.note import IncidentNote
from app.repositories.event_repository import EventRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.repositories.note_repository import IncidentNoteRepository
from app.schemas.ml import IncidentMLResponse
from app.schemas.note import IncidentNoteCreate, IncidentNoteResponse, IncidentNoteUpdate
from app.security.dependencies import require_permission
from app.security.permissions import Permission

router = APIRouter(
    prefix="/incidents",
    dependencies=[Depends(require_permission(Permission.SOC_READ))],
)
ReadUser = Annotated[User, Depends(require_permission(Permission.SOC_READ))]
AnalystUser = Annotated[User, Depends(require_permission(Permission.INCIDENTS_WRITE))]


@router.get("/{incident_id}/notes", response_model=list[IncidentNoteResponse])
async def list_notes(
    incident_id: uuid.UUID,
    actor: ReadUser,
    session: AsyncSession = Depends(get_db_session),
) -> list[IncidentNoteResponse]:
    if await IncidentRepository(session).get(incident_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    notes = await IncidentNoteRepository(session).list_for_incident(incident_id)
    return [IncidentNoteResponse.model_validate(note) for note in notes]


@router.post("/{incident_id}/notes", response_model=IncidentNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    incident_id: uuid.UUID,
    payload: IncidentNoteCreate,
    actor: AnalystUser,
    session: AsyncSession = Depends(get_db_session),
) -> IncidentNoteResponse:
    if await IncidentRepository(session).get(incident_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    note = await IncidentNoteRepository(session).create(
        IncidentNote(incident_id=incident_id, author_id=actor.id, content=payload.content)
    )
    await session.commit()
    return IncidentNoteResponse.model_validate(note)


@router.patch("/{incident_id}/notes/{note_id}", response_model=IncidentNoteResponse)
async def update_note(
    incident_id: uuid.UUID,
    note_id: uuid.UUID,
    payload: IncidentNoteUpdate,
    actor: AnalystUser,
    session: AsyncSession = Depends(get_db_session),
) -> IncidentNoteResponse:
    repository = IncidentNoteRepository(session)
    note = await repository.get(note_id)
    if note is None or note.incident_id != incident_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    if note.author_id != actor.id and actor.role_name != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the note author can update this note")
    note = await repository.update(note, payload.content)
    await session.commit()
    return IncidentNoteResponse.model_validate(note)


@router.get("/{incident_id}/ml", response_model=IncidentMLResponse)
async def get_incident_ml(
    incident_id: uuid.UUID,
    actor: ReadUser,
    session: AsyncSession = Depends(get_db_session),
) -> IncidentMLResponse:
    incident_repository = IncidentRepository(session)
    incident = await incident_repository.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    event_repository = EventRepository(session)
    event_id = next((entry.get("event_id") for entry in incident.timeline if entry.get("event_id")), None)
    event = await event_repository.get_by_event_id(event_id) if event_id else None
    if event is None:
        return IncidentMLResponse(
            status="unavailable", model_version=None, feature_version=None, score=None,
            threshold=None, is_anomaly=None, features={}, explanation=[], message="No event evidence is available",
        )
    try:
        score = await MLInferenceService(ModelRegistryRepository(session), get_settings()).score_event(
            event, event_repository
        )
    except (FileNotFoundError, ValueError) as exc:
        return IncidentMLResponse(
            status="unavailable", model_version=None, feature_version=None, score=None,
            threshold=None, is_anomaly=None, features={}, explanation=[], message=str(exc),
        )
    if score is None:
        return IncidentMLResponse(
            status="unavailable", model_version=None, feature_version=None, score=None,
            threshold=None, is_anomaly=None, features={}, explanation=[], message="No active ML model is available",
        )
    explanation = [
        f"{name}: {value:g}"
        for name, value in sorted(score.features.items(), key=lambda item: item[1], reverse=True)[:5]
    ]
    return IncidentMLResponse(
        status="available", model_version=score.model_version, feature_version=score.feature_version,
        score=score.score, threshold=score.threshold, is_anomaly=score.is_anomaly,
        features=score.features, explanation=explanation, message=None,
    )