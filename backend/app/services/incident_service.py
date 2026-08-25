from __future__ import annotations

import uuid

from app.repositories.incident_repository import IncidentRepository
from app.schemas.alert import AlertResponse
from app.schemas.incident import IncidentDetail, IncidentListItem, IncidentListResponse, IncidentQueryFilters, TimelineEntry


class IncidentService:
    def __init__(self, incident_repository: IncidentRepository) -> None:
        self.incident_repository = incident_repository

    async def list_incidents(self, filters: IncidentQueryFilters) -> IncidentListResponse:
        incidents, total = await self.incident_repository.list(filters)
        return IncidentListResponse(
            total=total,
            limit=filters.limit,
            offset=filters.offset,
            items=[IncidentListItem.model_validate(incident) for incident in incidents],
        )

    async def get_incident(self, incident_id: uuid.UUID) -> IncidentDetail | None:
        incident = await self.incident_repository.get(incident_id)
        if incident is None:
            return None
        alerts = await self.incident_repository.get_alerts_for_incident(incident_id)
        return IncidentDetail(
            **IncidentListItem.model_validate(incident).model_dump(),
            timeline=[TimelineEntry.model_validate(item) for item in incident.timeline],
            alerts=[AlertResponse.model_validate(alert) for alert in alerts],
        )
