from __future__ import annotations

import uuid

from datetime import UTC, datetime

from app.models.incident import Incident
from app.repositories.incident_repository import IncidentRepository
from app.repositories.mitre_repository import MitreRepository
from app.repositories.note_repository import IncidentNoteRepository
from app.schemas.alert import AlertResponse
from app.schemas.incident import (
    IncidentCreate,
    IncidentDetail,
    IncidentListItem,
    IncidentListResponse,
    IncidentQueryFilters,
    TimelineEntry,
)
from app.schemas.mitre import MitreTechniqueResponse
from app.schemas.note import IncidentNoteResponse


class IncidentService:
    def __init__(self, incident_repository: IncidentRepository, mitre_repository: MitreRepository, note_repository: IncidentNoteRepository) -> None:
        self.incident_repository = incident_repository
        self.mitre_repository = mitre_repository
        self.note_repository = note_repository

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
        techniques = await self.mitre_repository.get_for_rules([alert.rule_id for alert in alerts])
        notes = await self.note_repository.list_for_incident(incident_id)
        return IncidentDetail(
            **IncidentListItem.model_validate(incident).model_dump(),
            timeline=[TimelineEntry.model_validate(item) for item in incident.timeline],
            alerts=[AlertResponse.model_validate(alert) for alert in alerts],
            techniques=[MitreTechniqueResponse.model_validate(item) for item in techniques],
            notes=[IncidentNoteResponse.model_validate(note) for note in notes],
        )

    async def create_manual_incident(self, payload: IncidentCreate) -> IncidentDetail:
        now = datetime.now(UTC)
        severity_scores = {"low": 30, "medium": 55, "high": 80, "critical": 95}
        risk_score = severity_scores.get(payload.severity, 75)
        correlation_key = f"manual:{payload.primary_username or 'unknown'}:{payload.primary_source_ip or 'unknown'}:{uuid.uuid4().hex[:6]}"

        timeline = [
            {
                "timestamp": now.isoformat(),
                "type": "incident_created",
                "title": f"Incident created: {payload.title}",
                "description": payload.description,
                "username": payload.primary_username,
                "source_ip": payload.primary_source_ip,
                "metadata": {"source": "analyst_console", "preset": payload.preset_scenario},
            }
        ]

        incident = Incident(
            id=uuid.uuid4(),
            title=payload.title,
            description=payload.description,
            status="open",
            severity=payload.severity,
            risk_score=risk_score,
            correlation_key=correlation_key,
            primary_username=payload.primary_username or "analyst",
            primary_source_ip=payload.primary_source_ip or "192.168.1.10",
            first_seen=now,
            last_seen=now,
            timeline=timeline,
        )

        created = await self.incident_repository.create(incident)
        detail = await self.get_incident(created.id)
        if detail is None:
            raise RuntimeError("Failed to retrieve created incident")
        return detail

