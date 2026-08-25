from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AlertStatus = Literal["new", "acknowledged", "investigating", "resolved", "false_positive"]


class AlertCreate(BaseModel):
    rule_id: str
    event_id: uuid.UUID
    title: str
    description: str
    severity: str
    confidence: float
    status: AlertStatus = "new"
    source_ip: str | None = None
    username: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    first_seen: datetime
    last_seen: datetime


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_id: str
    event_id: uuid.UUID
    title: str
    description: str
    severity: str
    confidence: float
    status: str
    source_ip: str | None
    username: str | None
    evidence: dict[str, Any]
    first_seen: datetime
    last_seen: datetime
    created_at: datetime
