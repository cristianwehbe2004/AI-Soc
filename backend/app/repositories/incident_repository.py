from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.incident import Incident, IncidentAlert
from app.schemas.incident import IncidentQueryFilters


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, incident: Incident) -> Incident:
        self.session.add(incident)
        await self.session.flush()
        await self.session.refresh(incident)
        return incident

    async def add_alert_links(self, incident_id: uuid.UUID, alert_ids: list[uuid.UUID]) -> None:
        if not alert_ids:
            return
        existing_result = await self.session.execute(
            select(IncidentAlert.alert_id).where(
                IncidentAlert.incident_id == incident_id,
                IncidentAlert.alert_id.in_(alert_ids),
            )
        )
        existing = set(existing_result.scalars().all())
        links = [
            IncidentAlert(incident_id=incident_id, alert_id=alert_id)
            for alert_id in alert_ids
            if alert_id not in existing
        ]
        if links:
            self.session.add_all(links)
            await self.session.flush()

    async def update(self, incident: Incident) -> Incident:
        await self.session.flush()
        await self.session.refresh(incident)
        return incident

    async def find_open_related_incident(
        self,
        *,
        correlation_key: str,
        username: str | None,
        source_ip: str | None,
        since: datetime,
        until: datetime,
    ) -> Incident | None:
        identity_clauses = [Incident.correlation_key == correlation_key]
        if username is not None:
            identity_clauses.append(Incident.primary_username == username)
        if source_ip is not None:
            identity_clauses.append(Incident.primary_source_ip == source_ip)
        query = (
            select(Incident)
            .where(
                Incident.status == "open",
                or_(*identity_clauses),
                Incident.last_seen >= since,
                Incident.last_seen <= until,
            )
            .order_by(Incident.last_seen.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def acquire_correlation_lock(self, correlation_key: str) -> None:
        await self.session.execute(
            select(
                func.pg_advisory_xact_lock(
                    func.hashtextextended(correlation_key, 0)
                )
            )
        )

    async def list(self, filters: IncidentQueryFilters) -> tuple[list[Incident], int]:
        query = self._apply_filters(select(Incident), filters).order_by(Incident.last_seen.desc())
        count_query = self._apply_filters(select(func.count()).select_from(Incident), filters)
        result = await self.session.execute(query.limit(filters.limit).offset(filters.offset))
        total_result = await self.session.execute(count_query)
        return list(result.scalars().all()), int(total_result.scalar_one())

    async def get(self, incident_id: uuid.UUID) -> Incident | None:
        result = await self.session.execute(select(Incident).where(Incident.id == incident_id))
        return result.scalar_one_or_none()

    async def get_alerts_for_incident(self, incident_id: uuid.UUID) -> list[Alert]:
        result = await self.session.execute(
            select(Alert)
            .join(IncidentAlert, IncidentAlert.alert_id == Alert.id)
            .where(IncidentAlert.incident_id == incident_id)
            .order_by(Alert.first_seen.asc(), Alert.created_at.asc())
        )
        return list(result.scalars().all())

    def _apply_filters(self, query: Select, filters: IncidentQueryFilters) -> Select:
        if filters.status is not None:
            query = query.where(Incident.status == filters.status)
        if filters.severity is not None:
            query = query.where(Incident.severity == filters.severity)
        if filters.username is not None:
            query = query.where(Incident.primary_username == filters.username)
        if filters.source_ip is not None:
            query = query.where(Incident.primary_source_ip == filters.source_ip)
        return query
