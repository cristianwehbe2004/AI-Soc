from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

InvestigationStatus = Literal["queued", "running", "completed", "failed"]
AnalysisSeverity = Literal["low", "medium", "high", "critical"]
RecommendationPriority = Literal["low", "medium", "high", "urgent"]


class EvidenceFinding(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1, max_length=2000)
    severity: AnalysisSeverity
    confidence: float = Field(ge=0, le=1)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class EvidenceAnalysis(BaseModel):
    findings: list[EvidenceFinding] = Field(default_factory=list, max_length=20)
    gaps: list[str] = Field(default_factory=list, max_length=20)


class RiskAnalysis(BaseModel):
    score: int = Field(ge=0, le=100)
    severity: AnalysisSeverity
    rationale: str = Field(min_length=1, max_length=3000)
    factors: list[str] = Field(default_factory=list, max_length=20)


class MitreContextItem(BaseModel):
    technique_id: str
    name: str
    tactics: list[str]
    relevance: str


class InvestigationNarrative(BaseModel):
    executive_summary: str = Field(min_length=1, max_length=4000)
    attack_story: str = Field(min_length=1, max_length=6000)
    confidence: float = Field(ge=0, le=1)


class Recommendation(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    priority: RecommendationPriority
    rationale: str = Field(min_length=1, max_length=2000)
    actions: list[str] = Field(min_length=1, max_length=20)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class RecommendationSet(BaseModel):
    recommendations: list[Recommendation] = Field(min_length=1, max_length=20)


class InvestigationResult(BaseModel):
    executive_summary: str
    attack_story: str
    confidence: float = Field(ge=0, le=1)
    findings: list[EvidenceFinding]
    evidence_gaps: list[str]
    risk_analysis: RiskAnalysis
    mitre_context: list[MitreContextItem]
    recommendations: list[Recommendation]


class InvestigationContext(BaseModel):
    incident: dict[str, Any]
    alerts: list[dict[str, Any]]
    events: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    techniques: list[dict[str, Any]]
    valid_evidence_refs: list[str]


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    status: InvestigationStatus
    provider: str
    model: str
    prompt_version: str
    context_hash: str
    context_snapshot: dict[str, Any]
    result: InvestigationResult | None
    validation_errors: list[str]
    provider_response_ids: list[str]
    error: str | None
    input_tokens: int
    output_tokens: int
    attempt_count: int
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InvestigationListResponse(BaseModel):
    items: list[InvestigationResponse]
