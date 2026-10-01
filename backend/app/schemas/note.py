from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IncidentNoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class IncidentNoteUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class IncidentNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    created_at: datetime
    updated_at: datetime