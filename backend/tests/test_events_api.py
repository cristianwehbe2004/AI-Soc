from datetime import UTC, datetime
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.event import (
    EventBulkIngestResponse,
    EventIngestResponse,
    EventListResponse,
    EventResponse,
)
from conftest import AUTH_HEADERS


def test_create_event_validates_and_returns_created(monkeypatch) -> None:
    async def fake_create_event(self, payload):
        return EventIngestResponse(id=uuid4(), event_id=payload.event_id or "evt_test", accepted=True)

    monkeypatch.setattr("app.services.event_service.EventService.create_event", fake_create_event)

    client = TestClient(app)
    response = client.post(
        "/api/v1/events",
        headers=AUTH_HEADERS["api_key"],
        json={
            "timestamp": "2026-08-24T11:30:00Z",
            "source": "auth-service",
            "source_type": "application",
            "event_type": "login_failure",
            "category": "authentication",
            "username": "alice",
            "source_ip": "192.168.1.50",
            "status": "failed",
            "metadata": {"synthetic": True},
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["accepted"] is True
    assert response.json()["event_id"] == "evt_test"


def test_create_event_rejects_invalid_category() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/events",
        headers=AUTH_HEADERS["api_key"],
        json={
            "timestamp": "2026-08-24T11:30:00Z",
            "source": "auth-service",
            "source_type": "application",
            "event_type": "login_failure",
            "category": "not-real",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_bulk_create_events_returns_count(monkeypatch) -> None:
    async def fake_create_events_bulk(self, payload):
        return EventBulkIngestResponse(
            accepted=True,
            count=len(payload.events),
            events=[
                EventIngestResponse(id=uuid4(), event_id=f"evt_{index}", accepted=True)
                for index, _ in enumerate(payload.events, start=1)
            ],
        )

    monkeypatch.setattr("app.services.event_service.EventService.create_events_bulk", fake_create_events_bulk)

    client = TestClient(app)
    response = client.post(
        "/api/v1/events/bulk",
        headers=AUTH_HEADERS["api_key"],
        json={
            "events": [
                {
                    "timestamp": "2026-08-24T11:30:00Z",
                    "source": "auth-service",
                    "source_type": "application",
                    "event_type": "login_failure",
                    "category": "authentication",
                },
                {
                    "timestamp": "2026-08-24T11:31:00Z",
                    "source": "api-gateway",
                    "source_type": "application",
                    "event_type": "api_request",
                    "category": "api",
                },
            ]
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["count"] == 2


def test_list_events_returns_filtered_payload(monkeypatch) -> None:
    event = EventResponse(
        id=uuid4(),
        event_id="evt_123",
        timestamp=datetime(2026, 8, 24, 11, 30, tzinfo=UTC),
        received_at=datetime(2026, 8, 24, 11, 31, tzinfo=UTC),
        source="auth-service",
        source_type="application",
        event_type="login_failure",
        category="authentication",
        severity="medium",
        user_id=None,
        username="alice",
        source_ip="192.168.1.50",
        destination_ip=None,
        source_port=None,
        destination_port=None,
        hostname=None,
        device_id=None,
        action=None,
        status="failed",
        resource=None,
        resource_type=None,
        country=None,
        user_agent=None,
        bytes_sent=None,
        bytes_received=None,
        raw_payload={"synthetic": True},
        metadata={"synthetic": True},
        created_at=datetime(2026, 8, 24, 11, 31, tzinfo=UTC),
    )

    async def fake_list_events(self, filters):
        assert filters.username == "alice"
        return EventListResponse(total=1, limit=filters.limit, offset=filters.offset, items=[event])

    monkeypatch.setattr("app.services.event_service.EventService.list_events", fake_list_events)

    client = TestClient(app)
    response = client.get(
        "/api/v1/events",
        headers=AUTH_HEADERS["viewer"],
        params={"username": "alice", "limit": 10, "offset": 0},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["event_id"] == "evt_123"
