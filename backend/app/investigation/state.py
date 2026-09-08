from __future__ import annotations

from typing import Any, TypedDict

from app.schemas.investigation import (
    EvidenceAnalysis,
    InvestigationContext,
    InvestigationNarrative,
    InvestigationResult,
    MitreContextItem,
    RecommendationSet,
    RiskAnalysis,
)


class InvestigationState(TypedDict, total=False):
    investigation_id: str
    incident_id: str
    context: InvestigationContext
    timeline_analysis: dict[str, Any]
    evidence_analysis: EvidenceAnalysis
    risk_analysis: RiskAnalysis
    mitre_context: list[MitreContextItem]
    narrative: InvestigationNarrative
    recommendation_set: RecommendationSet
    result: InvestigationResult
    provider_response_ids: list[str]
    input_tokens: int
    output_tokens: int
