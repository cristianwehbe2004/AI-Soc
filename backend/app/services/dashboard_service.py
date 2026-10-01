from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.event import Event
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.model_registry import ModelRegistry
from app.schemas.dashboard import DashboardSummaryResponse


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self) -> DashboardSummaryResponse:
        events_total = await self._count(Event)
        incidents_open = await self._count(Incident, Incident.status.in_(("open", "investigating")))
        alerts_active = await self._count(Alert, Alert.status.not_in(("resolved", "false_positive")))
        investigations_active = await self._count(Investigation, Investigation.status.in_(("queued", "running")))
        model_result = await self.session.execute(
            select(ModelRegistry)
            .where(ModelRegistry.status == "active")
            .order_by(ModelRegistry.trained_at.desc())
            .limit(1)
        )
        model = model_result.scalar_one_or_none()
        return DashboardSummaryResponse(
            events_total=events_total,
            incidents_open=incidents_open,
            alerts_active=alerts_active,
            investigations_active=investigations_active,
            model_status="active" if model else "unavailable",
            model_version=model.model_version if model else None,
            as_of=datetime.now(UTC),
        )

    async def _count(self, model: type, *conditions) -> int:
        result = await self.session.execute(select(func.count()).select_from(model).where(*conditions))
        return int(result.scalar_one())