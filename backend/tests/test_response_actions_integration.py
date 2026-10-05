from datetime import UTC, datetime
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import app
from app.models.auth import AuthSession
from app.services.response_actions import execute_action
from conftest import AUTH_HEADERS
from sqlalchemy import select


@pytest.mark.anyio
async def test_asff_finding_and_separate_approval_for_app_containment():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        finding = {
            "Id": "example/finding-1", "AwsAccountId": "123456789012",
            "UpdatedAt": datetime.now(UTC).isoformat(), "Types": ["S3/Public exposure"],
            "Severity": {"Label": "HIGH"}, "Resources": [{"Id": "arn:aws:s3:::private-demo", "Type": "AwsS3Bucket"}],
        }
        first = await client.post("/api/v1/aws/findings/bulk", headers=AUTH_HEADERS["api_key"], json={"findings": [finding, finding]})
        assert first.status_code == 200, first.text
        assert first.json()["count"] == 1
        duplicate = await client.post("/api/v1/aws/findings/bulk", headers=AUTH_HEADERS["api_key"], json={"findings": [finding]})
        assert duplicate.status_code == 200 and duplicate.json()["count"] == 0
        archived = await client.post("/api/v1/aws/findings/bulk", headers=AUTH_HEADERS["api_key"], json={"findings": [{**finding, "Id": "example/archived", "RecordState": "ARCHIVED"}]})
        assert archived.status_code == 200 and archived.json()["count"] == 0
        incidents = (await client.get("/api/v1/incidents", headers=AUTH_HEADERS["viewer"])).json()["items"]
        assert len(incidents) == 1
        incident_id = incidents[0]["id"]
        detail = (await client.get(f"/api/v1/incidents/{incident_id}", headers=AUTH_HEADERS["viewer"])).json()
        assert any(alert["rule_id"] == "rule_006_cloud_finding" for alert in detail["alerts"])

        async with SessionLocal() as session:
            target = await session.scalar(select(AuthSession.user_id).limit(1))
        payload = {
            "action_type": "revoke_app_sessions", "target": str(target), "account_id": None,
            "rationale": "Confirmed suspicious cloud finding and account activity",
            "impact": "This user will be signed out on all devices",
            "evidence_refs": [f"alert:{detail['alerts'][0]['id']}"],
            "idempotency_key": "incident-containment-001",
        }
        viewer = await client.post(f"/api/v1/incidents/{incident_id}/response-actions", headers=AUTH_HEADERS["viewer"], json=payload)
        assert viewer.status_code == 403
        proposed = await client.post(f"/api/v1/incidents/{incident_id}/response-actions", headers=AUTH_HEADERS["analyst"], json=payload)
        assert proposed.status_code == 201, proposed.text
        action_id = proposed.json()["id"]
        self_approval = await client.post(f"/api/v1/response-actions/{action_id}/approve", headers=AUTH_HEADERS["analyst"])
        assert self_approval.status_code == 403
        approved = await client.post(f"/api/v1/response-actions/{action_id}/approve", headers=AUTH_HEADERS["admin"])
        assert approved.status_code == 202, approved.text
        await execute_action(uuid.UUID(action_id), SessionLocal, get_settings())
        result = await client.get(f"/api/v1/response-actions/{action_id}", headers=AUTH_HEADERS["viewer"])
        assert result.json()["status"] == "succeeded"
        async with SessionLocal() as session:
            active = await session.scalar(select(AuthSession.id).where(AuthSession.user_id == target, AuthSession.revoked_at.is_(None)))
        assert active is None
