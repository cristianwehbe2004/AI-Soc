from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EventCategory = Literal[
    "authentication",
    "network",
    "cloud",
    "application",
    "file_access",
    "privilege_change",
    "process",
    "api",
]

EventType = Literal[
    "login_success",
    "login_failure",
    "logout",
    "api_request",
    "api_error",
    "file_access",
    "file_download",
    "privilege_change",
    "network_connection",
    "network_scan",
    "resource_access",
    "account_created",
    "account_deleted",
    "password_changed",
]

EventSeverity = Literal["low", "medium", "high", "critical"]


class EventIngestBase(BaseModel):
    timestamp: datetime
    source: str = Field(min_length=1, max_length=255)
    source_type: str = Field(min_length=1, max_length=64)
    event_type: EventType
    category: EventCategory
    severity: EventSeverity | None = None
    event_id: str | None = Field(default=None, max_length=128)
    user_id: str | None = Field(default=None, max_length=128)
    username: str | None = Field(default=None, max_length=255)
    source_ip: str | None = Field(default=None, max_length=64)
    destination_ip: str | None = Field(default=None, max_length=64)
    source_port: int | None = Field(default=None, ge=0, le=65535)
    destination_port: int | None = Field(default=None, ge=0, le=65535)
    hostname: str | None = Field(default=None, max_length=255)
    device_id: str | None = Field(default=None, max_length=255)
    action: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, max_length=64)
    resource: str | None = Field(default=None, max_length=255)
    resource_type: str | None = Field(default=None, max_length=128)
    country: str | None = Field(default=None, max_length=128)
    user_agent: str | None = None
    bytes_sent: int | None = Field(default=None, ge=0)
    bytes_received: int | None = Field(default=None, ge=0)
    raw_payload: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def ensure_timestamp_has_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class EventCreate(EventIngestBase):
    pass


class EventBulkCreate(BaseModel):
    events: list[EventCreate] = Field(min_length=1, max_length=1000)


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    event_id: str
    timestamp: datetime
    received_at: datetime
    source: str
    source_type: str
    event_type: str
    category: str
    severity: str | None
    user_id: str | None
    username: str | None
    source_ip: str | None
    destination_ip: str | None
    source_port: int | None
    destination_port: int | None
    hostname: str | None
    device_id: str | None
    action: str | None
    status: str | None
    resource: str | None
    resource_type: str | None
    country: str | None
    user_agent: str | None
    bytes_sent: int | None
    bytes_received: int | None
    raw_payload: dict[str, Any]
    metadata: dict[str, Any] = Field(alias="event_metadata")
    created_at: datetime


class EventIngestResponse(BaseModel):
    id: uuid.UUID
    event_id: str
    accepted: bool = True


class EventBulkIngestResponse(BaseModel):
    accepted: bool = True
    count: int
    events: list[EventIngestResponse]


class EventListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[EventResponse]


class EventQueryFilters(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    event_type: EventType | None = None
    category: EventCategory | None = None
    source_ip: str | None = None
    username: str | None = None
    severity: EventSeverity | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

