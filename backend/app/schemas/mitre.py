from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MitreTechniqueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    external_id: str
    name: str
    description: str
    tactics: list[str]
    platforms: list[str]
    version: str
    source_url: str
    is_subtechnique: bool
    parent_external_id: str | None
    created_at: datetime
    updated_at: datetime


class MitreTechniqueListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[MitreTechniqueResponse]


class RuleTechniqueResponse(BaseModel):
    rule_id: str
    techniques: list[MitreTechniqueResponse]
