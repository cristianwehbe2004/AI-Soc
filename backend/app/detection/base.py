from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from app.models.event import Event


@dataclass(slots=True)
class DetectionResult:
    rule_id: str
    title: str
    description: str
    severity: str
    confidence: float
    source_ip: str | None
    username: str | None
    event_id: str
    evidence: dict[str, Any] = field(default_factory=dict)
    first_seen: datetime | None = None
    last_seen: datetime | None = None


@dataclass(slots=True)
class DetectionContext:
    event_repository: Any
    settings: Any


class DetectionRule(Protocol):
    id: str
    name: str
    severity: str

    async def evaluate(self, event: Event, context: DetectionContext) -> DetectionResult | None:
        ...
