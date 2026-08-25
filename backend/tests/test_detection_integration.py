from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.db.session import SessionLocal
from app.repositories.alert_repository import AlertRepository
from app.schemas.event import EventBulkCreate, EventCreate
from app.services.event_service import EventService


def make_event(**overrides) -> EventCreate:
    base = {
        "timestamp": datetime(2026, 8, 25, 10, 0, tzinfo=UTC),
        "source": "test-source",
        "source_type": "application",
        "event_type": "login_failure",
        "category": "authentication",
        "severity": "medium",
        "username": "alice",
        "source_ip": "203.0.113.50",
        "status": "failed",
        "metadata": {"test": True},
    }
    base.update(overrides)
    return EventCreate(**base)


async def fetch_alerts():
    async with SessionLocal() as session:
        return await AlertRepository(session).list_all()


@pytest.mark.asyncio
async def test_bulk_failed_login_burst_creates_bruteforce_and_password_spray_alerts() -> None:
    now = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)
    events = [
        make_event(
            timestamp=now - timedelta(seconds=10 - index),
            username=f"user{index % 5}",
            event_id=f"evt_burst_{index}",
        )
        for index in range(10)
    ]

    async with SessionLocal() as session:
        service = EventService(session)
        await service.create_events_bulk(EventBulkCreate(events=events))

    alerts = await fetch_alerts()
    rule_ids = {alert.rule_id for alert in alerts}

    assert "rule_001_brute_force" in rule_ids
    assert "rule_002_password_spray" in rule_ids


@pytest.mark.asyncio
async def test_privilege_change_sequence_creates_alert() -> None:
    now = datetime(2026, 8, 25, 11, 0, tzinfo=UTC)
    events = [
        make_event(timestamp=now - timedelta(minutes=5), event_id="evt_priv_fail_1", username="admin", source_ip="198.51.100.10"),
        make_event(timestamp=now - timedelta(minutes=1), event_id="evt_priv_fail_2", username="admin", source_ip="198.51.100.10"),
        make_event(
            timestamp=now,
            event_id="evt_priv_change",
            source="iam",
            source_type="cloud",
            event_type="privilege_change",
            category="privilege_change",
            severity="high",
            username="admin",
            source_ip="198.51.100.10",
            action="role_escalation",
            status="success",
        ),
    ]

    async with SessionLocal() as session:
        service = EventService(session)
        await service.create_events_bulk(EventBulkCreate(events=events))

    alerts = await fetch_alerts()

    assert any(alert.rule_id == "rule_003_suspicious_privilege_change" for alert in alerts)


@pytest.mark.asyncio
async def test_large_download_creates_alert() -> None:
    async with SessionLocal() as session:
        service = EventService(session)
        await service.create_event(
            make_event(
                event_id="evt_large_download",
                event_type="file_download",
                category="file_access",
                severity="medium",
                username="bob",
                source_ip="192.0.2.20",
                resource="/exports/customers.csv",
                bytes_received=2_000_000,
                status="success",
            )
        )

    alerts = await fetch_alerts()

    assert any(alert.rule_id == "rule_004_large_download" for alert in alerts)


@pytest.mark.asyncio
async def test_login_after_failures_creates_alert() -> None:
    now = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    events = [
        make_event(timestamp=now - timedelta(minutes=10), event_id="evt_login_fail_1", username="charlie", source_ip="192.0.2.44"),
        make_event(timestamp=now - timedelta(minutes=6), event_id="evt_login_fail_2", username="charlie", source_ip="192.0.2.44"),
        make_event(timestamp=now - timedelta(minutes=2), event_id="evt_login_fail_3", username="charlie", source_ip="192.0.2.44"),
        make_event(
            timestamp=now,
            event_id="evt_login_success",
            event_type="login_success",
            category="authentication",
            severity="low",
            username="charlie",
            source_ip="192.0.2.44",
            status="success",
        ),
    ]

    async with SessionLocal() as session:
        service = EventService(session)
        await service.create_events_bulk(EventBulkCreate(events=events))

    alerts = await fetch_alerts()

    assert any(alert.rule_id == "rule_005_login_after_failures" for alert in alerts)


@pytest.mark.asyncio
async def test_normal_benign_event_creates_no_alerts() -> None:
    async with SessionLocal() as session:
        service = EventService(session)
        await service.create_event(
            make_event(
                event_id="evt_normal",
                event_type="api_request",
                category="api",
                severity="low",
                username="dana",
                source_ip="192.168.1.5",
                status="success",
            )
        )

    alerts = await fetch_alerts()

    assert alerts == []
