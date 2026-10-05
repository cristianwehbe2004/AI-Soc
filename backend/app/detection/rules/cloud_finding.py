from __future__ import annotations

from app.detection.base import DetectionContext, DetectionResult
from app.models.event import Event


class CloudFindingRule:
    id = "rule_006_cloud_finding"
    name = "Cloud or identity security finding"
    severity = "high"

    async def evaluate(self, event: Event, context: DetectionContext) -> DetectionResult | None:
        if event.event_type not in {
            "cloud_finding", "s3_public_exposure", "secret_exposure",
            "access_key_used", "data_exfiltration",
        }:
            return None
        metadata = event.event_metadata or {}
        finding_type = str(metadata.get("finding_type") or event.event_type)[:128]
        severity = event.severity or "medium"
        return DetectionResult(
            rule_id=self.id,
            title=f"Security finding: {finding_type}",
            description=f"{event.source} reported {finding_type} on {event.resource or 'an asset'}.",
            severity=severity,
            confidence=0.9 if event.source_type == "aws_security_hub" else 0.75,
            source_ip=event.source_ip,
            username=event.username,
            event_id=event.event_id,
            evidence={
                "finding_type": finding_type,
                "resource": event.resource,
                "account_id": metadata.get("account_id"),
                "provider_finding_id": metadata.get("provider_finding_id"),
            },
            first_seen=event.timestamp,
            last_seen=event.timestamp,
        )
