from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.alert import AlertResponse

IncidentStatus = Literal["open", "investigating", "contained", "resolved"]
IncidentSeverity = Literal["low", "medium", "high", "critical"]


class TimelineEntry(BaseModel):
    timestamp: datetime
    type: str
    title: str
    description: str
    event_id: str | None = None
    alert_id: uuid.UUID | None = None
    rule_id: str | None = None
    username: str | None = None
    source_ip: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    status: str
    severity: str
    risk_score: int
    primary_username: str | None
    primary_source_ip: str | None
    first_seen: datetime
    last_seen: datetime
    created_at: datetime
    updated_at: datetime


class IncidentDetail(IncidentListItem):
    timeline: list[TimelineEntry]
    alerts: list[AlertResponse]


class IncidentListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[IncidentListItem]


class IncidentQueryFilters(BaseModel):
    status: IncidentStatus | None = None
    severity: IncidentSeverity | None = None
    username: str | None = None
    source_ip: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
