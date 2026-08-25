from __future__ import annotations

from datetime import timedelta

from app.detection.base import DetectionContext, DetectionResult
from app.models.event import Event


class BruteForceRule:
    id = "rule_001_brute_force"
    name = "Brute Force"
    severity = "high"

    async def evaluate(self, event: Event, context: DetectionContext) -> DetectionResult | None:
        if event.event_type != "login_failure" or not event.source_ip:
            return None

        window_seconds = context.settings.brute_force_window_seconds
        failures = await context.event_repository.recent_login_failures_by_source_ip(
            source_ip=event.source_ip,
            since=event.timestamp - timedelta(seconds=window_seconds),
            until=event.timestamp,
        )
        if len(failures) < context.settings.brute_force_threshold:
            return None

        return DetectionResult(
            rule_id=self.id,
            title="Potential brute-force attack detected",
            description=f"Detected {len(failures)} login failures from {event.source_ip} within {window_seconds} seconds.",
            severity=self.severity,
            confidence=0.9,
            source_ip=event.source_ip,
            username=event.username,
            event_id=event.event_id,
            evidence={
                "failure_count": len(failures),
                "window_seconds": window_seconds,
                "event_ids": [failure.event_id for failure in failures],
            },
            first_seen=failures[0].timestamp,
            last_seen=failures[-1].timestamp,
        )
