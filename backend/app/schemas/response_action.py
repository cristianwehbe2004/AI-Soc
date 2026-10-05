from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ActionType = Literal["revoke_app_sessions", "disable_aws_access_key", "block_s3_public_access"]
ActionStatus = Literal["proposed", "approved", "running", "succeeded", "failed", "rejected"]


class ResponseActionCreate(BaseModel):
    action_type: ActionType
    target: str = Field(min_length=1, max_length=512)
    account_id: str | None = Field(default=None, pattern=r"^\d{12}$")
    rationale: str = Field(min_length=10, max_length=2000)
    impact: str = Field(min_length=10, max_length=2000)
    evidence_refs: list[str] = Field(min_length=1, max_length=20)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_target(self):
        if self.action_type == "revoke_app_sessions":
            uuid.UUID(self.target)
            if self.account_id is not None:
                raise ValueError("App actions must not specify an AWS account")
        elif self.account_id is None:
            raise ValueError("AWS actions require a 12-digit account ID")
        return self


class ResponseActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    incident_id: uuid.UUID
    action_type: ActionType
    target: str
    account_id: str | None
    status: ActionStatus
    rationale: str
    impact: str
    evidence_refs: list[str]
    idempotency_key: str
    proposed_by: uuid.UUID
    approved_by: uuid.UUID | None
    result: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime
