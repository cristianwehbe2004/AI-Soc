from __future__ import annotations

from datetime import timedelta

from app.detection.base import DetectionContext, DetectionResult
from app.models.event import Event


class PasswordSprayRule:
    id = "rule_002_password_spray"
    name = "Password Spray"
    severity = "high"

    async def evaluate(self, event: Event, context: DetectionContext) -> DetectionResult | None:
        if event.event_type != "login_failure" or not event.source_ip:
            return None

        window_seconds = context.settings.password_spray_window_seconds
        usernames = await context.event_repository.distinct_usernames_for_failures_by_source_ip(
            source_ip=event.source_ip,
            since=event.timestamp - timedelta(seconds=window_seconds),
            until=event.timestamp,
        )
        if len(usernames) < context.settings.password_spray_unique_users:
            return None

        failures = await context.event_repository.recent_login_failures_by_source_ip(
            source_ip=event.source_ip,
            since=event.timestamp - timedelta(seconds=window_seconds),
            until=event.timestamp,
        )
        return DetectionResult(
            rule_id=self.id,
            title="Potential password spray detected",
            description=f"Detected login failures against {len(usernames)} users from {event.source_ip} within {window_seconds} seconds.",
            severity=self.severity,
            confidence=0.88,
            source_ip=event.source_ip,
            username=event.username,
            event_id=event.event_id,
            evidence={
                "unique_users": sorted(usernames),
                "unique_user_count": len(usernames),
                "window_seconds": window_seconds,
            },
            first_seen=failures[0].timestamp if failures else event.timestamp,
            last_seen=event.timestamp,
        )
