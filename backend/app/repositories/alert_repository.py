from __future__ import annotations

from sqlalchemy import select
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
