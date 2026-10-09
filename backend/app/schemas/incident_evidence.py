from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EvidenceKind = Literal["analyst_observation", "network_observation", "asset_configuration", "identity_activity", "vulnerability_report"]
Zone = Literal["internet", "dmz", "internal", "restricted", "unknown"]


class NetworkObservation(BaseModel):
    source_zone: Zone
    destination_zone: Zone
    destination_port: int = Field(ge=1, le=65535)
    protocol: Literal["tcp", "udp"] = "tcp"
    disposition: Literal["allowed", "blocked", "unknown"]


class IncidentEvidenceCreate(BaseModel):
    kind: EvidenceKind
    source: str = Field(min_length=3, max_length=160)
    summary: str = Field(min_length=8, max_length=2000)
    network: NetworkObservation | None = None
    observed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_network(self):
        if self.kind == "network_observation" and self.network is None:
            raise ValueError("Network observations require structured network details")
        if self.kind != "network_observation" and self.network is not None:
            raise ValueError("Network details are only valid for network observations")
        return self


class IncidentEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    submitted_by: uuid.UUID
    kind: EvidenceKind
    source: str
    summary: str
    network: NetworkObservation | None
    observed_at: datetime | None
    sensitive_redacted: bool
    created_at: datetime
