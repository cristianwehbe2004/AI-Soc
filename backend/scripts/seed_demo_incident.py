from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import uuid

from app.db.session import SessionLocal
from app.schemas.event import EventBulkCreate, EventCreate
from app.services.event_service import EventService


async def seed_demo_data() -> None:
    now = datetime.now(UTC)
    username = "victim-admin"
    source_ip = "198.51.100.60"

    events = [
        # Burst of 10 failed logins within 20 seconds
        EventCreate(
            event_id=f"demo_evt_fail_{i}_{uuid.uuid4().hex[:6]}",
            timestamp=now - timedelta(seconds=60 - i * 2),
            source="auth-service",
            source_type="application",
            event_type="login_failure",
            category="authentication",
            severity="medium",
            username=username,
            source_ip=source_ip,
            status="failed",
            metadata={"attempt": i},
        )
        for i in range(12)
    ]

    # Successful login after failures
    events.append(
        EventCreate(
            event_id=f"demo_evt_success_{uuid.uuid4().hex[:6]}",
            timestamp=now - timedelta(seconds=35),
            source="auth-service",
            source_type="application",
            event_type="login_success",
            category="authentication",
            severity="low",
            username=username,
            source_ip=source_ip,
            status="success",
            metadata={"mfa_bypassed": True},
        )
    )

    # Privilege escalation
    events.append(
        EventCreate(
            event_id=f"demo_evt_priv_escalation_{uuid.uuid4().hex[:6]}",
            timestamp=now - timedelta(seconds=20),
            source="iam-cloud",
            source_type="cloud",
            event_type="privilege_change",
            category="privilege_change",
            severity="high",
            username=username,
            source_ip=source_ip,
            action="role_escalation",
            status="success",
            metadata={"granted_role": "GlobalAdmin"},
        )
    )

    # Large exfiltration download
    events.append(
        EventCreate(
            event_id=f"demo_evt_exfiltration_{uuid.uuid4().hex[:6]}",
            timestamp=now - timedelta(seconds=5),
            source="dlp-storage",
            source_type="application",
            event_type="file_download",
            category="file_access",
            severity="high",
            username=username,
            source_ip=source_ip,
            resource="/sensitive/customer_database_export.dmp",
            bytes_received=5_000_000,
            status="success",
            metadata={"classification": "CONFIDENTIAL"},
        )
    )

    async with SessionLocal() as session:
        service = EventService(session)
        result = await service.create_events_bulk(EventBulkCreate(events=events))
        print(f"Successfully seeded {result.count} demo security events for {username} ({source_ip})")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
