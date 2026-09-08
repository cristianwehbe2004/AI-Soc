from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.redis import redis_client
from app.db.session import get_db_session
from app.investigation.queue import InvestigationQueue
from app.repositories.incident_repository import IncidentRepository
from app.repositories.investigation_repository import InvestigationRepository
from app.schemas.investigation import (
    InvestigationListResponse,
    InvestigationResponse,
)
from app.services.investigation_service import (
    InvestigationDisabledError,
    InvestigationQueueError,
    InvestigationService,
)

router = APIRouter()


def get_investigation_service(
    session: AsyncSession = Depends(get_db_session),
) -> InvestigationService:
    settings = get_settings()
    return InvestigationService(
        session=session,
        incident_repository=IncidentRepository(session),
        investigation_repository=InvestigationRepository(session),
        queue=InvestigationQueue(
            redis_client,
            queue_key=settings.investigation_queue_key,
        ),
        settings=settings,
    )


@router.post(
    "/incidents/{incident_id}/investigations",
    response_model=InvestigationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_investigation(
    incident_id: uuid.UUID,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationResponse:
    try:
        investigation = await service.request_investigation(incident_id)
    except InvestigationDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except InvestigationQueueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )
    return investigation


@router.get(
    "/incidents/{incident_id}/investigations",
    response_model=InvestigationListResponse,
)
async def list_incident_investigations(
    incident_id: uuid.UUID,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationListResponse:
    result = await service.list_for_incident(incident_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )
    return result


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationResponse,
)
async def get_investigation(
    investigation_id: uuid.UUID,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationResponse:
    investigation = await service.get_investigation(investigation_id)
    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation
