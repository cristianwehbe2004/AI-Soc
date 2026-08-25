from __future__ import annotations

from datetime import timedelta

from app.detection.base import DetectionContext, DetectionResult
from app.models.event import Event


class LoginAfterFailuresRule:
    id = "rule_005_login_after_failures"
    name = "Login After Failures"
    severity = "high"

    async def evaluate(self, event: Event, context: DetectionContext) -> DetectionResult | None:
        if event.event_type != "login_success":
            return None

        window_seconds = context.settings.login_after_failures_window_seconds
        failures = await context.event_repository.recent_login_failures_for_identity(
            username=event.username,
            source_ip=event.source_ip,
            since=event.timestamp - timedelta(seconds=window_seconds),
            until=event.timestamp,
        )
        if len(failures) < context.settings.login_after_failures_threshold:
            return None

        return DetectionResult(
            rule_id=self.id,
            title="Login after multiple failures detected",
            description="Successful login followed multiple recent failures for the same user or source IP.",
            severity=self.severity,
            confidence=0.86,
            source_ip=event.source_ip,
            username=event.username,
            event_id=event.event_id,
            evidence={
                "failure_count": len(failures),
                "threshold": context.settings.login_after_failures_threshold,
                "failure_event_ids": [failure.event_id for failure in failures],
                "window_seconds": window_seconds,
            },
            first_seen=failures[0].timestamp,
            last_seen=event.timestamp,
        )
