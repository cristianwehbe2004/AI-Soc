from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.schemas.event import EventQueryFilters


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, event: Event) -> Event:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def create_many(self, events: list[Event]) -> list[Event]:
        self.session.add_all(events)
        await self.session.flush()
        for event in events:
            await self.session.refresh(event)
        return events

    async def get_by_event_id(self, event_id: str) -> Event | None:
        result = await self.session.execute(select(Event).where(Event.event_id == event_id))
        return result.scalar_one_or_none()

    async def list(self, filters: EventQueryFilters) -> tuple[list[Event], int]:
        query = self._apply_filters(select(Event), filters).order_by(Event.timestamp.desc())
        count_query = self._apply_filters(select(func.count()).select_from(Event), filters)

        result = await self.session.execute(query.limit(filters.limit).offset(filters.offset))
        total_result = await self.session.execute(count_query)

        return list(result.scalars().all()), int(total_result.scalar_one())

    async def recent_login_failures_by_source_ip(
        self,
        *,
        source_ip: str,
        since: datetime,
        until: datetime,
    ) -> list[Event]:
        result = await self.session.execute(
            select(Event)
            .where(
                Event.event_type == "login_failure",
                Event.source_ip == source_ip,
                Event.timestamp >= since,
                Event.timestamp <= until,
            )
            .order_by(Event.timestamp.asc())
        )
        return list(result.scalars().all())

    async def distinct_usernames_for_failures_by_source_ip(
        self,
        *,
        source_ip: str,
        since: datetime,
        until: datetime,
    ) -> list[str]:
        result = await self.session.execute(
            select(Event.username)
            .where(
                Event.event_type == "login_failure",
                Event.source_ip == source_ip,
                Event.username.is_not(None),
                Event.timestamp >= since,
                Event.timestamp <= until,
            )
            .distinct()
        )
        return [username for username in result.scalars().all() if username is not None]

    async def recent_login_failures_for_identity(
        self,
        *,
        username: str | None,
        source_ip: str | None,
        since: datetime,
        until: datetime,
    ) -> list[Event]:
        query = select(Event).where(
            Event.event_type == "login_failure",
            Event.timestamp >= since,
            Event.timestamp <= until,
        )
        identity_clauses = []
        if username is not None:
            identity_clauses.append(Event.username == username)
        if source_ip is not None:
            identity_clauses.append(Event.source_ip == source_ip)
        if not identity_clauses:
            return []
        query = query.where(identity_clauses[0] if len(identity_clauses) == 1 else or_(*identity_clauses))
        result = await self.session.execute(query.order_by(Event.timestamp.asc()))
        return list(result.scalars().all())

    async def recent_authentication_context_for_privilege_change(
        self,
        *,
        username: str | None,
        source_ip: str | None,
        lookback_seconds: int,
        event_time: datetime,
    ) -> list[Event]:
        since = event_time - timedelta(seconds=lookback_seconds)
        return await self.recent_login_failures_for_identity(
            username=username,
            source_ip=source_ip,
            since=since,
            until=event_time,
        )

    def _apply_filters(self, query: Select, filters: EventQueryFilters) -> Select:
        if filters.start_time is not None:
            query = query.where(Event.timestamp >= filters.start_time)
        if filters.end_time is not None:
            query = query.where(Event.timestamp <= filters.end_time)
        if filters.event_type is not None:
            query = query.where(Event.event_type == filters.event_type)
        if filters.category is not None:
            query = query.where(Event.category == filters.category)
        if filters.source_ip is not None:
            query = query.where(Event.source_ip == filters.source_ip)
        if filters.username is not None:
            query = query.where(Event.username == filters.username)
        if filters.severity is not None:
            query = query.where(Event.severity == filters.severity)
        return query
