from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class IncidentMLResponse(BaseModel):
    status: Literal["available", "unavailable"]
    model_version: str | None
    feature_version: str | None
    score: float | None
    threshold: float | None
    is_anomaly: bool | None
    features: dict[str, float]
    explanation: list[str]
    message: str | None