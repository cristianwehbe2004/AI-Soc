from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.correlation.risk_scoring import RiskScoringEngine
from app.correlation.service import IncidentCorrelationService
from app.correlation.timeline import build_incident_timeline
from app.models.alert import Alert
from app.models.event import Event


def build_alert(rule_id: str, *, username: str = "alice", source_ip: str = "203.0.113.10", at: datetime) -> Alert:
    return Alert(
        id=uuid4(),
        rule_id=rule_id,
        event_id=uuid4(),
        title=rule_id,
        description=f"Alert for {rule_id}",
        severity="high" if rule_id != "rule_004_large_download" else "medium",
        confidence=0.9,
        status="new",
        source_ip=source_ip,
        username=username,
        evidence={"rule_id": rule_id},
        first_seen=at,
        last_seen=at,
        created_at=at,
    )


def build_event(event_id: str, *, at: datetime, username: str = "alice", source_ip: str = "203.0.113.10") -> Event:
    return Event(
        id=uuid4(),
        event_id=event_id,
        timestamp=at,
        source="synthetic-auth",
        source_type="application",
        event_type="login_failure",
        category="authentication",
        severity="medium",
        username=username,
        source_ip=source_ip,
        status="failed",
        raw_payload={"test": True},
        event_metadata={},
    )


def build_settings() -> SimpleNamespace:
    return SimpleNamespace(
        risk_score_high_severity_weight=20,
        risk_score_medium_severity_weight=10,
        risk_score_low_severity_weight=5,
        risk_score_confidence_multiplier=20,
        risk_score_combo_bonus=15,
        risk_score_supporting_bonus=10,
        credential_compromise_lookback_seconds=1800,
        incident_merge_window_seconds=3600,
    )


def test_risk_score_and_severity_bucketing() -> None:
    settings = build_settings()
    engine = RiskScoringEngine(settings)
    now = datetime.now(UTC)
    alerts = [
        build_alert("rule_001_brute_force", at=now),
        build_alert("rule_005_login_after_failures", at=now + timedelta(minutes=1)),
        build_alert("rule_003_suspicious_privilege_change", at=now + timedelta(minutes=2)),
    ]

    score = engine.score(alerts)

    assert score >= 85
    assert engine.severity_from_score(score) == "critical"


def test_timeline_generator_orders_events_and_alerts() -> None:
    now = datetime.now(UTC)
    event = build_event("evt-1", at=now)
    alert = build_alert("rule_001_brute_force", at=now + timedelta(seconds=30))
    alert.event_id = event.id

    timeline = build_incident_timeline([alert], {event.id: event})

    assert [entry["type"] for entry in timeline] == ["event", "alert"]
    assert timeline[0]["event_id"] == "evt-1"
    assert timeline[1]["rule_id"] == "rule_001_brute_force"


@pytest.mark.anyio
async def test_correlation_candidates_require_initial_access_and_success() -> None:
    service = IncidentCorrelationService(
        alert_repository=SimpleNamespace(),
        event_repository=SimpleNamespace(),
        incident_repository=SimpleNamespace(),
        settings=build_settings(),
    )
    now = datetime.now(UTC)
    alerts = [
        build_alert("rule_001_brute_force", at=now),
        build_alert("rule_003_suspicious_privilege_change", at=now + timedelta(minutes=1)),
    ]

    assert service._credential_compromise_candidates(alerts) == []

    alerts.append(build_alert("rule_005_login_after_failures", at=now + timedelta(minutes=2)))
    candidates = service._credential_compromise_candidates(alerts)
    assert {alert.rule_id for alert in candidates} == {
        "rule_001_brute_force",
        "rule_003_suspicious_privilege_change",
        "rule_005_login_after_failures",
    }
