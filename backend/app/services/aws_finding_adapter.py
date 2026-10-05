from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.event import EventCreate


class ASFFBatch(BaseModel):
    findings: list[dict[str, Any]] = Field(min_length=1, max_length=100)


def asff_to_event(finding: dict[str, Any]) -> EventCreate:
    """Convert one Security Hub finding without storing arbitrary vendor payloads."""
    finding_id = finding.get("Id")
    account = finding.get("AwsAccountId")
    if not isinstance(finding_id, str) or not finding_id or not isinstance(account, str) or len(account) != 12 or not account.isdigit():
        raise ValueError("Finding requires Id and AwsAccountId")
    updated = finding.get("UpdatedAt") or finding.get("CreatedAt")
    if not isinstance(updated, str):
        raise ValueError("Finding requires UpdatedAt or CreatedAt")
    timestamp = datetime.fromisoformat(updated.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    resources = finding.get("Resources") or []
    if not isinstance(resources, list):
        raise ValueError("Finding Resources must be a list")
    resource = resources[0] if resources and isinstance(resources[0], dict) else {}
    types = finding.get("Types") or ["cloud_finding"]
    if not isinstance(types, list) or not types or not isinstance(types[0], str):
        raise ValueError("Finding Types must be a non-empty list of strings")
    kind = types[0][:128]
    label = str(finding.get("Title") or kind)[:255]
    severity_data = finding.get("Severity") or {}
    if not isinstance(severity_data, dict):
        raise ValueError("Finding Severity must be an object")
    severity_label = str(severity_data.get("Label") or "MEDIUM").lower()
    severity = severity_label if severity_label in {"low", "medium", "high", "critical"} else "medium"
    digest = hashlib.sha256(f"{account}:{finding_id}:{updated}".encode()).hexdigest()
    event_type = "s3_public_exposure" if "s3" in kind.lower() and "public" in kind.lower() else "cloud_finding"
    return EventCreate(
        event_id=f"asff_{digest}",
        timestamp=timestamp,
        source="aws_security_hub",
        source_type="aws_security_hub",
        event_type=event_type,
        category="security_finding",
        severity=severity,
        resource=str(resource.get("Id") or "")[:255] or None,
        resource_type=str(resource.get("Type") or "")[:128] or None,
        metadata={
            "account_id": account[:64],
            "provider_finding_id": finding_id[:512],
            "finding_type": kind,
            "title": label,
            "region": str(finding.get("Region") or "")[:64],
        },
        raw_payload={},
    )
