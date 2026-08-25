from __future__ import annotations

from app.detection.base import DetectionContext, DetectionResult
from app.detection.registry import RuleRegistry
from app.models.alert import Alert
from app.models.event import Event


class DetectionEngine:
    def __init__(self, registry: RuleRegistry) -> None:
        self.registry = registry

    async def evaluate_event(self, event: Event, context: DetectionContext) -> list[DetectionResult]:
        matches: list[DetectionResult] = []
        for rule in self.registry.all():
            result = await rule.evaluate(event, context)
            if result is not None:
                matches.append(result)
        return matches

    def build_alerts(self, event: Event, matches: list[DetectionResult]) -> list[Alert]:
        alerts: list[Alert] = []
        for match in matches:
            alerts.append(
                Alert(
                    rule_id=match.rule_id,
                    event_id=event.id,
                    title=match.title,
                    description=match.description,
                    severity=match.severity,
                    confidence=match.confidence,
                    status="new",
                    source_ip=match.source_ip,
                    username=match.username,
                    evidence=match.evidence,
                    first_seen=match.first_seen or event.timestamp,
                    last_seen=match.last_seen or event.timestamp,
                )
            )
        return alerts
