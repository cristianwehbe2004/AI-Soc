from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import SessionLocal
from app.main import app
from app.models.incident import Incident
from conftest import AUTH_HEADERS


@pytest.mark.anyio
async def test_dashboard_summary_returns_contract_defaults() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=AUTH_HEADERS["viewer"],
    ) as client:
        response = await client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    assert response.json() == {
        "events_total": 0,
        "incidents_open": 0,
        "alerts_active": 0,
        "investigations_active": 0,
        "model_status": "unavailable",
        "model_version": None,
        "as_of": response.json()["as_of"],
    }


@pytest.mark.anyio
async def test_analyst_notes_are_persisted_and_returned_in_incident_detail() -> None:
    incident_id = None
    async with SessionLocal() as session:
        incident = Incident(
            title="Test incident",
            description="Incident created for the notes contract.",
            status="open",
            severity="high",
            risk_score=80,
            correlation_key="test-notes",
            primary_username="analyst-target",
            primary_source_ip="203.0.113.10",
            first_seen=datetime.now(UTC),
            last_seen=datetime.now(UTC),
            timeline=[],
        )
        session.add(incident)
        await session.commit()
        incident_id = incident.id

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=AUTH_HEADERS["analyst"],
    ) as client:
        create_response = await client.post(
            f"/api/v1/incidents/{incident_id}/notes",
            json={"content": "Reviewed the correlated evidence."},
        )
        assert create_response.status_code == 201
        note = create_response.json()

        list_response = await client.get(f"/api/v1/incidents/{incident_id}/notes")
        assert list_response.status_code == 200
        assert list_response.json()[0]["content"] == "Reviewed the correlated evidence."

        detail_response = await client.get(f"/api/v1/incidents/{incident_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["notes"][0]["id"] == note["id"]