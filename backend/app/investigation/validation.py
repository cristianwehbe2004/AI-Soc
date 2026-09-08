from __future__ import annotations

from app.schemas.investigation import InvestigationResult


class InvestigationValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_investigation_result(
    result: InvestigationResult,
    *,
    valid_evidence_refs: set[str],
) -> None:
    errors: list[str] = []
    expected_severity = _severity_from_score(result.risk_analysis.score)
    if result.risk_analysis.severity != expected_severity:
        errors.append(
            "Risk severity does not match the deterministic score bucket: "
            f"expected {expected_severity}."
        )

    for finding in result.findings:
        if not finding.evidence_refs:
            errors.append(f"Finding '{finding.title}' has no evidence references.")
        _validate_refs(
            finding.evidence_refs,
            valid_evidence_refs,
            f"finding '{finding.title}'",
            errors,
        )
    for recommendation in result.recommendations:
        if not recommendation.evidence_refs:
            errors.append(
                f"Recommendation '{recommendation.title}' has no evidence references."
            )
        _validate_refs(
            recommendation.evidence_refs,
            valid_evidence_refs,
            f"recommendation '{recommendation.title}'",
            errors,
        )

    if errors:
        raise InvestigationValidationError(errors)


def _validate_refs(
    references: list[str],
    valid_references: set[str],
    label: str,
    errors: list[str],
) -> None:
    unknown = sorted(set(references) - valid_references)
    if unknown:
        errors.append(f"Unknown evidence references in {label}: {', '.join(unknown)}")


def _severity_from_score(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"
