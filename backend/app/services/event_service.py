from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.detection import build_detection_engine
from app.detection.base import DetectionContext
from app.repositories.alert_repository import AlertRepository
from app.repositories.event_repository import EventRepository
from app.core.config import get_settings
from app.correlation import IncidentCorrelationService
from app.schemas.event import (
    EventBulkCreate,
    EventBulkIngestResponse,
    EventCreate,
    EventIngestResponse,
    EventListResponse,
    EventQueryFilters,
    EventResponse,
)
from app.services.event_normalizer import get_normalizer
from app.repositories.incident_repository import IncidentRepository
from app.ml.inference import MLInferenceService
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.db.redis import redis_client
from app.realtime.events import RealtimePublisher
from app.schemas.alert import AlertResponse
from app.schemas.incident import IncidentListItem
from app.investigation.automation import AutomaticInvestigationDispatcher

logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = EventRepository(session)
        self.alert_repository = AlertRepository(session)
        self.incident_repository = IncidentRepository(session)
        self.model_registry_repository = ModelRegistryRepository(session)
        self.settings = get_settings()
        self.detection_engine = build_detection_engine()
        self.ml_inference_service = MLInferenceService(self.model_registry_repository, self.settings)
        self.correlation_service = IncidentCorrelationService(
            alert_repository=self.alert_repository,
            event_repository=self.repository,
            incident_repository=self.incident_repository,
            settings=self.settings,
        )
        self.realtime = RealtimePublisher(
            redis_client,
            channel_prefix=self.settings.realtime_redis_channel_prefix,
        )

    async def create_event(self, payload: EventCreate) -> EventIngestResponse:
        event = get_normalizer(payload).normalize(payload)
        created = await self.repository.create(event)
        alerts = await self._run_detection([created])
        incidents = []
        if alerts:
            incidents = await self.correlation_service.correlate(alerts)
        await self.session.commit()
        await self._publish_realtime(created, alerts, incidents)
        await AutomaticInvestigationDispatcher(self.session, redis_client, self.settings).dispatch(incidents)
        return EventIngestResponse(id=created.id, event_id=created.event_id, accepted=True)

    async def create_events_bulk(self, payload: EventBulkCreate) -> EventBulkIngestResponse:
        events = [get_normalizer(item).normalize(item) for item in payload.events]
        created = []
        realtime_items = []
        for event in events:
            created_event = await self.repository.create(event)
            created.append(created_event)
            alerts = await self._run_detection([created_event])
            incidents = []
            if alerts:
                incidents = await self.correlation_service.correlate(alerts)
            realtime_items.append((created_event, alerts, incidents, set(self.correlation_service.last_created_ids)))
        await self.session.commit()
        all_incidents = {incident.id: incident for _, _, incidents, _ in realtime_items for incident in incidents}
        await AutomaticInvestigationDispatcher(self.session, redis_client, self.settings).dispatch(all_incidents.values())
        for created_event, alerts, incidents, created_ids in realtime_items:
            await self._publish_realtime(created_event, alerts, incidents, created_ids=created_ids)
        items = [EventIngestResponse(id=event.id, event_id=event.event_id, accepted=True) for event in created]
        return EventBulkIngestResponse(accepted=True, count=len(items), events=items)

    async def list_events(self, filters: EventQueryFilters) -> EventListResponse:
        events, total = await self.repository.list(filters)
        return EventListResponse(
            total=total,
            limit=filters.limit,
            offset=filters.offset,
            items=[EventResponse.model_validate(event) for event in events],
        )

    async def get_event(self, event_id: str) -> EventResponse | None:
        event = await self.repository.get_by_event_id(event_id)
        if event is None:
            return None
        return EventResponse.model_validate(event)

    async def _run_detection(self, events) -> list:
        context = DetectionContext(
            event_repository=self.repository,
            settings=self.settings,
            ml_inference_service=self.ml_inference_service,
        )
        alerts = []
        for event in events:
            matches = await self.detection_engine.evaluate_event(event, context)
            alerts.extend(self.detection_engine.build_alerts(event, matches))
        if alerts:
            return await self.alert_repository.create_many(alerts)
        return []

    async def _publish_realtime(self, event, alerts, incidents, *, created_ids: set | None = None) -> None:
        created_ids = created_ids if created_ids is not None else set(self.correlation_service.last_created_ids)
        try:
            event_payload = EventResponse.model_validate(event).model_dump(mode="json")
            await self.realtime.publish(
                "event.created",
                entity_id=event.event_id,
                payload=event_payload,
            )
            for alert in alerts:
                alert_payload = AlertResponse.model_validate(alert).model_dump(mode="json")
                await self.realtime.publish(
                    "alert.created",
                    entity_id=str(alert.id),
                    payload=alert_payload,
                )
            for incident in incidents:
                incident_payload = IncidentListItem.model_validate(incident).model_dump(mode="json")
                event_type = "incident.created" if incident.id in created_ids else "incident.updated"
                await self.realtime.publish(
                    event_type,
                    entity_id=str(incident.id),
                    payload=incident_payload,
                    version=int(incident.updated_at.timestamp() * 1_000_000),
                )
        except Exception:
            logger.exception("Realtime publication failed after successful event commit")
