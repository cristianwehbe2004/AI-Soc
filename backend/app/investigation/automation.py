from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.investigation.queue import InvestigationQueue
from app.models.incident import Incident
from app.repositories.incident_repository import IncidentRepository
from app.repositories.investigation_repository import InvestigationRepository
from app.services.investigation_service import InvestigationService

logger = logging.getLogger(__name__)

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


class AutomaticInvestigationPolicy:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def should_trigger(self, incident: Incident) -> bool:
        if not self.settings.automatic_investigations_enabled:
            return False
        if incident.status not in {"open", "investigating"}:
            return False
        minimum = SEVERITY_RANK.get(self.settings.automatic_investigation_min_severity.lower(), 4)
        return SEVERITY_RANK.get(incident.severity.lower(), 0) >= minimum


class AutomaticInvestigationDispatcher:
    def __init__(self, session: AsyncSession, redis: Redis, settings: Settings) -> None:
        self.session = session
        self.redis = redis
        self.settings = settings
        self.policy = AutomaticInvestigationPolicy(settings)
        self.service = InvestigationService(
            session=session,
            incident_repository=IncidentRepository(session),
            investigation_repository=InvestigationRepository(session),
            queue=InvestigationQueue(redis, queue_key=settings.investigation_queue_key),
            settings=settings,
        )

    async def dispatch(self, incidents: Iterable[Incident]) -> None:
        for incident in incidents:
            if not self.policy.should_trigger(incident):
                continue
            if not await self._claim_cooldown(incident.id):
                continue
            try:
                await self.service.request_investigation(incident.id)
            except Exception:
                await self.redis.delete(self._cooldown_key(incident.id))
                logger.exception(
                    "Automatic investigation dispatch failed",
                    extra={"incident_id": str(incident.id)},
                )

    async def _claim_cooldown(self, incident_id: uuid.UUID) -> bool:
        result = await self.redis.set(
            self._cooldown_key(incident_id),
            "1",
            ex=self.settings.automatic_investigation_cooldown_seconds,
            nx=True,
        )
        return bool(result)

    def _cooldown_key(self, incident_id: uuid.UUID) -> str:
        return f"{self.settings.investigation_queue_key}:automatic:{incident_id}"