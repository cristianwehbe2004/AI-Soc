import pytest
from pydantic import ValidationError

from app.investigation.network_assessment import assess_network_evidence
from app.schemas.incident_evidence import IncidentEvidenceCreate
from app.services.incident_evidence import redact_secrets


def test_allowed_internet_management_path_produces_cited_review_action():
    assessment = assess_network_evidence([{
        "ref": "evidence:123", "kind": "network_observation", "source": "firewall log",
        "network": {"source_zone": "internet", "destination_zone": "restricted", "destination_port": 3389,
                    "protocol": "tcp", "disposition": "allowed"},
    }])
    assert len(assessment.findings) == 1
    assert assessment.findings[0].severity == "high"
    assert "not an independently verified" in assessment.findings[0].summary
    assert assessment.findings[0].evidence_refs == ["evidence:123"]
    assert assessment.recommendations[0].evidence_refs == ["evidence:123"]
    assert "Verify" in assessment.recommendations[0].actions[0]


def test_blocked_path_is_not_called_a_network_weakness():
    assessment = assess_network_evidence([{
        "ref": "evidence:123", "kind": "network_observation", "source": "firewall log",
        "network": {"source_zone": "internet", "destination_zone": "restricted", "destination_port": 3389,
                    "protocol": "tcp", "disposition": "blocked"},
    }])
    assert assessment.findings == []
    assert assessment.recommendations == []
    assert "does not prove" in assessment.gaps[0]


def test_missing_network_details_and_sensitive_strings_are_handled():
    with pytest.raises(ValidationError):
        IncidentEvidenceCreate(kind="network_observation", source="firewall", summary="Observed an allowed connection")
    cleaned, redacted = redact_secrets("password=hunter2 token:abc123 AKIA1234567890123456")
    assert redacted
    assert "hunter2" not in cleaned and "abc123" not in cleaned and "AKIA1234567890123456" not in cleaned
