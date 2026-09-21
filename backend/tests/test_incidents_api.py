from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.correlation.identity import build_correlation_key
from app.db.session import SessionLocal
from app.models.alert import Alert
from app.models.event import Event
from app.models.incident import Incident, IncidentAlert
from app.repositories.alert_repository import AlertRepository
from app.repositories.incident_repository import IncidentRepository
from conftest import AUTH_HEADERS


def credential_compromise_events(
    now: datetime,
    *,
    source_ip: str = "198.51.100.60",
) -> list[dict]:
    events = []
    for index in range(10):
        events.append(
            {
                "timestamp": (now - timedelta(minutes=10) + timedelta(seconds=index)).isoformat(),
                "source": "synthetic-auth",
                "source_type": "application",
                "event_type": "login_failure",
                "category": "authentication",
                "severity": "medium",
                "username": f"victim{index % 5}",
                "source_ip": source_ip,
                "status": "failed",
                "raw_payload": {"scenario": "credential-compromise", "sequence": index + 1},
                "metadata": {"synthetic": True, "scenario": "credential-compromise"},
            }
        )
    events.extend(
        [
            {
                "timestamp": (now - timedelta(minutes=2)).isoformat(),
                "source": "synthetic-auth",
                "source_type": "application",
                "event_type": "login_failure",
                "category": "authentication",
                "severity": "medium",
                "username": "victim-admin",
                "source_ip": source_ip,
                "status": "failed",
                "raw_payload": {"scenario": "credential-compromise", "sequence": 11},
                "metadata": {"synthetic": True, "scenario": "credential-compromise"},
            },
            {
                "timestamp": (now - timedelta(minutes=1)).isoformat(),
                "source": "synthetic-auth",
                "source_type": "application",
                "event_type": "login_success",
                "category": "authentication",
                "severity": "low",
                "username": "victim-admin",
                "source_ip": source_ip,
                "status": "success",
                "raw_payload": {"scenario": "credential-compromise", "sequence": 12},
                "metadata": {"synthetic": True, "scenario": "credential-compromise"},
            },
            {
                "timestamp": now.isoformat(),
                "source": "synthetic-iam",
                "source_type": "cloud",
                "event_type": "privilege_change",
                "category": "privilege_change",
                "severity": "high",
                "username": "victim-admin",
                "source_ip": source_ip,
                "status": "success",
                "action": "role_escalation",
                "raw_payload": {"scenario": "credential-compromise", "sequence": 13},
                "metadata": {"synthetic": True, "scenario": "credential-compromise"},
            },
        ]
    )
    return events


@pytest.mark.anyio
async def test_incident_apis_return_correlated_credential_compromise() -> None:
    now = datetime.now(UTC)
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers=AUTH_HEADERS["viewer"],
    ) as client:
        ingest_response = await client.post(
            "/api/v1/events/bulk",
            headers=AUTH_HEADERS["api_key"],
            json={"events": credential_compromise_events(now)},
        )
        assert ingest_response.status_code == 201

        list_response = await client.get("/api/v1/incidents")
        assert list_response.status_code == 200
        payload = list_response.json()
        assert payload["total"] == 1
        incident = payload["items"][0]
        assert incident["status"] == "open"
        assert incident["severity"] in {"high", "critical"}
        assert incident["primary_source_ip"] == "198.51.100.60"

        detail_response = await client.get(f"/api/v1/incidents/{incident['id']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert len(detail["alerts"]) >= 3
        assert any(entry["type"] == "alert" for entry in detail["timeline"])
        assert any(alert["rule_id"] == "rule_005_login_after_failures" for alert in detail["alerts"])
        assert {item["external_id"] for item in detail["techniques"]} == {
            "T1098",
            "T1078",
            "T1110",
            "T1110.003",
        }


@pytest.mark.anyio
async def test_benign_events_do_not_create_incidents() -> None:
    now = datetime.now(UTC)
    transport = ASGITransport(app=app)
    payload = {
        "events": [
            {
                "timestamp": (now - timedelta(minutes=1)).isoformat(),
                "source": "synthetic-auth",
                "source_type": "application",
                "event_type": "login_success",
                "category": "authentication",
                "severity": "low",
                "username": "alice",
                "source_ip": "192.168.1.10",
                "status": "success",
                "raw_payload": {"scenario": "benign"},
                "metadata": {"synthetic": True, "scenario": "benign"},
            }
        ]
    }

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers=AUTH_HEADERS["viewer"],
    ) as client:
        ingest_response = await client.post(
            "/api/v1/events/bulk", headers=AUTH_HEADERS["api_key"], json=payload
        )
        assert ingest_response.status_code == 201
        list_response = await client.get("/api/v1/incidents")
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 0


@pytest.mark.anyio
async def test_related_alerts_merge_into_existing_incident() -> None:
    now = datetime.now(UTC)
    transport = ASGITransport(app=app)

    phase_one = {"events": credential_compromise_events(now)[:-1]}
    phase_two = {
        "events": [
            {
                "timestamp": now.isoformat(),
                "source": "synthetic-storage",
                "source_type": "application",
                "event_type": "file_download",
                "category": "file_access",
                "severity": "medium",
                "username": "victim-admin",
                "source_ip": "198.51.100.60",
                "status": "success",
                "resource": "/exports/secrets.csv",
                "bytes_received": 2500000,
                "raw_payload": {"scenario": "credential-compromise", "sequence": 14},
                "metadata": {"synthetic": True, "scenario": "credential-compromise"},
            }
        ]
    }

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers=AUTH_HEADERS["viewer"],
    ) as client:
        first_response = await client.post(
            "/api/v1/events/bulk", headers=AUTH_HEADERS["api_key"], json=phase_one
        )
        assert first_response.status_code == 201

        second_response = await client.post(
            "/api/v1/events/bulk", headers=AUTH_HEADERS["api_key"], json=phase_two
        )
        assert second_response.status_code == 201

        list_response = await client.get("/api/v1/incidents")
        assert list_response.status_code == 200
        payload = list_response.json()
        assert payload["total"] == 1

        incident_id = payload["items"][0]["id"]
        detail_response = await client.get(f"/api/v1/incidents/{incident_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert any(alert["rule_id"] == "rule_004_large_download" for alert in detail["alerts"])


@pytest.mark.anyio
async def test_related_alert_lookup_uses_bounded_activity_time() -> None:
    now = datetime.now(UTC)
    activity_times = {
        "inside": now - timedelta(minutes=10),
        "before": now - timedelta(minutes=20),
        "after": now + timedelta(minutes=5),
    }

    async with SessionLocal() as session:
        alerts = []
        for label, activity_time in activity_times.items():
            event = Event(
                event_id=f"bounded-{label}",
                timestamp=activity_time,
                source="test-auth",
                source_type="application",
                event_type="login_failure",
                category="authentication",
                severity="medium",
                username="bounded-user",
                source_ip="203.0.113.91",
                status="failed",
                raw_payload={},
                event_metadata={},
            )
            session.add(event)
            await session.flush()
            alert = Alert(
                rule_id="rule_001_brute_force",
                event_id=event.id,
                title=label,
                description=label,
                severity="high",
                confidence=0.9,
                source_ip=event.source_ip,
                username=event.username,
                evidence={},
                first_seen=activity_time,
                last_seen=activity_time,
                created_at=now,
            )
            session.add(alert)
            alerts.append(alert)
        await session.flush()

        related = await AlertRepository(session).related_alerts(
            username="bounded-user",
            source_ip="203.0.113.91",
            since=now - timedelta(minutes=15),
            until=now,
        )

        assert [alert.title for alert in related] == ["inside"]


@pytest.mark.anyio
async def test_incident_merge_preserves_all_linked_alerts_in_timeline() -> None:
    now = datetime.now(UTC)
    old_at = now - timedelta(minutes=45)
    username = "victim-admin"
    source_ip = "198.51.100.60"
    correlation_key = build_correlation_key(
        username,
        source_ip,
    )

    async with SessionLocal() as session:
        old_event = Event(
            event_id="old-linked-event",
            timestamp=old_at,
            source="synthetic-storage",
            source_type="application",
            event_type="file_download",
            category="file_access",
            severity="medium",
            username=username,
            source_ip=source_ip,
            status="success",
            resource="/archive/old.csv",
            bytes_received=2_500_000,
            raw_payload={},
            event_metadata={},
        )
        session.add(old_event)
        await session.flush()
        old_alert = Alert(
            rule_id="rule_004_large_download",
            event_id=old_event.id,
            title="Old linked download",
            description="Existing evidence outside the current correlation lookback.",
            severity="medium",
            confidence=0.8,
            source_ip=source_ip,
            username=username,
            evidence={"bytes_received": 2_500_000},
            first_seen=old_at,
            last_seen=old_at,
        )
        session.add(old_alert)
        await session.flush()
        incident = Incident(
            title="Credential compromise incident",
            description="Existing incident",
            status="open",
            severity="medium",
            risk_score=30,
            correlation_key=correlation_key,
            primary_username=username,
            primary_source_ip=source_ip,
            first_seen=old_at,
            last_seen=old_at,
            timeline=[],
        )
        session.add(incident)
        await session.flush()
        session.add(IncidentAlert(incident_id=incident.id, alert_id=old_alert.id))
        await session.commit()
        incident_id = incident.id
        old_alert_id = str(old_alert.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers=AUTH_HEADERS["viewer"],
    ) as client:
        response = await client.post(
            "/api/v1/events/bulk",
            headers=AUTH_HEADERS["api_key"],
            json={
                "events": credential_compromise_events(
                    now,
                    source_ip="198.51.100.61",
                )
            },
        )
        assert response.status_code == 201
        detail_response = await client.get(f"/api/v1/incidents/{incident_id}")

    assert detail_response.status_code == 200
    detail = detail_response.json()
    linked_alert_ids = {alert["id"] for alert in detail["alerts"]}
    timeline_alert_ids = {
        entry["alert_id"]
        for entry in detail["timeline"]
        if entry["type"] == "alert"
    }
    assert old_alert_id in linked_alert_ids
    assert timeline_alert_ids == linked_alert_ids


@pytest.mark.anyio
async def test_concurrent_ingests_create_one_correlated_incident() -> None:
    now = datetime.now(UTC)
    payload = {"events": credential_compromise_events(now)[:-1]}
    transport_one = ASGITransport(app=app)
    transport_two = ASGITransport(app=app)

    async with (
        AsyncClient(
            transport=transport_one,
            base_url="http://testserver",
            headers=AUTH_HEADERS["viewer"],
        ) as client_one,
        AsyncClient(
            transport=transport_two,
            base_url="http://testserver",
            headers=AUTH_HEADERS["viewer"],
        ) as client_two,
    ):
        responses = await asyncio.gather(
            client_one.post(
                "/api/v1/events/bulk", headers=AUTH_HEADERS["api_key"], json=payload
            ),
            client_two.post(
                "/api/v1/events/bulk", headers=AUTH_HEADERS["api_key"], json=payload
            ),
        )
        list_response = await client_one.get("/api/v1/incidents")

    assert [response.status_code for response in responses] == [201, 201]
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1


@pytest.mark.anyio
async def test_correlation_lock_serializes_matching_transactions() -> None:
    now = datetime.now(UTC)
    correlation_key = build_correlation_key(
        "lock-user",
        "203.0.113.92",
    )

    async with SessionLocal() as first_session, SessionLocal() as second_session:
        first_repository = IncidentRepository(first_session)
        second_repository = IncidentRepository(second_session)
        await first_repository.acquire_correlation_lock(correlation_key)
        await first_repository.create(
            Incident(
                title="Credential compromise incident",
                description="Lock test",
                status="open",
                severity="low",
                risk_score=0,
                correlation_key=correlation_key,
                primary_username="lock-user",
                primary_source_ip="203.0.113.92",
                first_seen=now,
                last_seen=now,
                timeline=[],
            )
        )

        second_lock = asyncio.create_task(
            second_repository.acquire_correlation_lock(correlation_key)
        )
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(second_lock), timeout=0.1)

        await first_session.commit()
        await asyncio.wait_for(second_lock, timeout=1)
        incident = await second_repository.find_open_related_incident(
            correlation_key=correlation_key,
            username="lock-user",
            source_ip="203.0.113.92",
            since=now - timedelta(minutes=1),
            until=now + timedelta(minutes=1),
        )

        assert incident is not None
        await second_session.rollback()
