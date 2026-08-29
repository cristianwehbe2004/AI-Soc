from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.config import get_settings
from app.detection.base import DetectionContext, DetectionResult
from app.detection.engine import DetectionEngine
from app.detection.registry import RuleRegistry
from app.detection.rules import BruteForceRule
from app.models.event import Event


class MatchingRule:
    id = "test.match"
    name = "Matching Rule"
    severity = "high"

    async def evaluate(self, event, context):
        return DetectionResult(
            rule_id=self.id,
            title="Matched",
            description="Matched event",
            severity=self.severity,
            confidence=0.9,
            source_ip=event.source_ip,
            username=event.username,
            event_id=event.event_id,
            evidence={"matched": True},
            first_seen=event.timestamp,
            last_seen=event.timestamp,
        )


class NonMatchingRule:
    id = "test.no_match"
    name = "Non Matching Rule"
    severity = "low"

    async def evaluate(self, event, context):
        return None


class StubEventRepository:
    async def recent_login_failures_by_source_ip(self, **kwargs):
        return []


def test_rule_registry_gets_rules_by_id() -> None:
    matching = MatchingRule()
    registry = RuleRegistry([NonMatchingRule(), matching])

    assert registry.get("test.match") is matching
    assert registry.get("test.unknown") is None


def test_rule_registry_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="Duplicate detection rule id: test.match"):
        RuleRegistry([MatchingRule(), MatchingRule()])


def build_event(**overrides) -> Event:
    return Event(
        event_id=overrides.get("event_id", "evt_test"),
        timestamp=overrides.get("timestamp", datetime(2026, 8, 25, 10, 0, tzinfo=UTC)),
        received_at=overrides.get("received_at", datetime(2026, 8, 25, 10, 0, tzinfo=UTC)),
        source=overrides.get("source", "test-source"),
        source_type=overrides.get("source_type", "application"),
        event_type=overrides.get("event_type", "login_failure"),
        category=overrides.get("category", "authentication"),
        severity=overrides.get("severity", "medium"),
        username=overrides.get("username", "alice"),
        source_ip=overrides.get("source_ip", "203.0.113.10"),
        raw_payload=overrides.get("raw_payload", {}),
        event_metadata=overrides.get("event_metadata", {}),
        created_at=overrides.get("created_at", datetime(2026, 8, 25, 10, 0, tzinfo=UTC)),
    )


@pytest.mark.asyncio
async def test_rule_registry_and_engine_return_only_matches() -> None:
    engine = DetectionEngine(RuleRegistry([NonMatchingRule(), MatchingRule()]))
    event = build_event()
    context = DetectionContext(event_repository=StubEventRepository(), settings=get_settings())

    results = await engine.evaluate_event(event, context)

    assert len(results) == 1
    assert results[0].rule_id == "test.match"


@pytest.mark.asyncio
async def test_engine_builds_alert_models_from_results() -> None:
    engine = DetectionEngine(RuleRegistry([]))
    event = build_event()
    matches = [
        DetectionResult(
            rule_id="test.match",
            title="Matched",
            description="Matched event",
            severity="high",
            confidence=0.95,
            source_ip=event.source_ip,
            username=event.username,
            event_id=event.event_id,
            evidence={"matched": True},
            first_seen=event.timestamp,
            last_seen=event.timestamp,
        )
    ]

    alerts = engine.build_alerts(event, matches)

    assert len(alerts) == 1
    assert alerts[0].rule_id == "test.match"
    assert alerts[0].event_id == event.id


@pytest.mark.asyncio
async def test_brute_force_rule_does_not_match_below_threshold() -> None:
    class Repo:
        async def recent_login_failures_by_source_ip(self, **kwargs):
            return [build_event(event_id=f"evt_{index}") for index in range(9)]

    rule = BruteForceRule()
    context = DetectionContext(event_repository=Repo(), settings=get_settings())

    result = await rule.evaluate(build_event(), context)

    assert result is None
