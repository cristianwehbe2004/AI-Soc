from __future__ import annotations

from app.detection.base import DetectionContext, DetectionResult
from app.models.event import Event


class SuspiciousPrivilegeChangeRule:
    id = "rule_003_suspicious_privilege_change"
    name = "Suspicious Privilege Change"
    severity = "high"

    async def evaluate(self, event: Event, context: DetectionContext) -> DetectionResult | None:
        if event.event_type != "privilege_change":
            return None

        failures = await context.event_repository.recent_authentication_context_for_privilege_change(
            username=event.username,
            source_ip=event.source_ip,
            lookback_seconds=context.settings.privilege_change_lookback_seconds,
            event_time=event.timestamp,
        )
        if not failures:
            return None

        return DetectionResult(
            rule_id=self.id,
            title="Suspicious privilege change detected",
            description="Privilege change followed recent failed authentication activity for the same identity or source IP.",
            severity=self.severity,
            confidence=0.82,
            source_ip=event.source_ip,
            username=event.username,
            event_id=event.event_id,
            evidence={
                "lookback_seconds": context.settings.privilege_change_lookback_seconds,
                "failure_event_ids": [failure.event_id for failure in failures],
                "failure_count": len(failures),
            },
            first_seen=failures[0].timestamp,
            last_seen=event.timestamp,
        )
