from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, alert: Alert) -> Alert:
        self.session.add(alert)
        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def create_many(self, alerts: list[Alert]) -> list[Alert]:
        self.session.add_all(alerts)
        await self.session.flush()
        for alert in alerts:
            await self.session.refresh(alert)
        return alerts

    async def list_all(self) -> list[Alert]:
        result = await self.session.execute(select(Alert).order_by(Alert.created_at.asc()))
        return list(result.scalars().all())

    async def related_alerts(
        self,
        *,
        username: str | None,
        source_ip: str | None,
        since: datetime,
        until: datetime,
        exclude_alert_ids: list | None = None,
    ) -> list[Alert]:
        clauses = []
        if username is not None:
            clauses.append(Alert.username == username)
        if source_ip is not None:
            clauses.append(Alert.source_ip == source_ip)
        if not clauses:
            return []
        query = select(Alert).where(
            Alert.last_seen >= since,
            Alert.last_seen <= until,
            clauses[0] if len(clauses) == 1 else or_(*clauses),
        )
        if exclude_alert_ids:
            query = query.where(Alert.id.not_in(exclude_alert_ids))
        result = await self.session.execute(query.order_by(Alert.first_seen.asc(), Alert.created_at.asc()))
        return list(result.scalars().all())
