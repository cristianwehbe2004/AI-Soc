from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.detection import build_detection_engine
from app.detection.base import DetectionContext
from app.repositories.alert_repository import AlertRepository
from app.repositories.event_repository import EventRepository
from app.core.config import get_settings
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


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = EventRepository(session)
        self.alert_repository = AlertRepository(session)
        self.settings = get_settings()
        self.detection_engine = build_detection_engine()

    async def create_event(self, payload: EventCreate) -> EventIngestResponse:
        event = get_normalizer(payload).normalize(payload)
        created = await self.repository.create(event)
        await self._run_detection([created])
        await self.session.commit()
        return EventIngestResponse(id=created.id, event_id=created.event_id, accepted=True)

    async def create_events_bulk(self, payload: EventBulkCreate) -> EventBulkIngestResponse:
        events = [get_normalizer(item).normalize(item) for item in payload.events]
        created = []
        for event in events:
            created_event = await self.repository.create(event)
            created.append(created_event)
            await self._run_detection([created_event])
        await self.session.commit()
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

    async def _run_detection(self, events) -> None:
        context = DetectionContext(event_repository=self.repository, settings=self.settings)
        alerts = []
        for event in events:
            matches = await self.detection_engine.evaluate_event(event, context)
            alerts.extend(self.detection_engine.build_alerts(event, matches))
        if alerts:
            await self.alert_repository.create_many(alerts)
