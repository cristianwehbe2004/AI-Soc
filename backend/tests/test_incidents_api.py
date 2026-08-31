from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.session import SessionLocal
from app.models.incident import Incident


def credential_compromise_events(now: datetime) -> list[dict]:
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
                "source_ip": "198.51.100.60",
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
                "source_ip": "198.51.100.60",
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
                "source_ip": "198.51.100.60",
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
                "source_ip": "198.51.100.60",
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

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ingest_response = await client.post("/api/v1/events/bulk", json={"events": credential_compromise_events(now)})
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

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ingest_response = await client.post("/api/v1/events/bulk", json=payload)
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

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_response = await client.post("/api/v1/events/bulk", json=phase_one)
        assert first_response.status_code == 201

        second_response = await client.post("/api/v1/events/bulk", json=phase_two)
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
