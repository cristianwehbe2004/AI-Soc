from __future__ import annotations

from app.detection.base import DetectionContext, DetectionResult
from app.models.event import Event


class LargeDownloadRule:
    id = "rule_004_large_download"
    name = "Large Download"
    severity = "medium"

    async def evaluate(self, event: Event, context: DetectionContext) -> DetectionResult | None:
        if event.event_type not in {"file_download", "resource_access"}:
            return None
        if event.bytes_received is None or event.bytes_received < context.settings.large_download_threshold_bytes:
            return None

        return DetectionResult(
            rule_id=self.id,
            title="Large download detected",
            description=f"Detected download volume of {event.bytes_received} bytes above threshold.",
            severity=self.severity,
            confidence=0.8,
            source_ip=event.source_ip,
            username=event.username,
            event_id=event.event_id,
            evidence={
                "bytes_received": event.bytes_received,
                "threshold_bytes": context.settings.large_download_threshold_bytes,
                "resource": event.resource,
            },
            first_seen=event.timestamp,
            last_seen=event.timestamp,
        )
