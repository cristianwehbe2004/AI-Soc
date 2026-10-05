from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.ml.incident_classifier import FEATURES, LabeledCase, features_for_events
from app.schemas.response_action import ResponseActionCreate
from app.services.aws_finding_adapter import asff_to_event


def test_asff_conversion_strips_untrusted_payload_and_keeps_finding_identity():
    finding = {
        "Id": "finding/1", "AwsAccountId": "123456789012",
        "UpdatedAt": "2026-10-05T10:00:00Z", "Types": ["S3/Public exposure"],
        "Severity": {"Label": "CRITICAL"}, "Resources": [{"Id": "arn:aws:s3:::private-demo", "Type": "AwsS3Bucket"}],
        "Description": "secret material should not be stored",
    }
    event = asff_to_event(finding)
    assert event.event_type == "s3_public_exposure"
    assert event.severity == "critical"
    assert event.metadata["provider_finding_id"] == "finding/1"
    assert event.raw_payload == {}
    assert "secret material" not in str(event.model_dump())
    assert event.event_id == asff_to_event(finding).event_id


def test_asff_rejects_invalid_account_and_types():
    finding = {"Id": "x", "AwsAccountId": "bad", "UpdatedAt": "2026-10-05T10:00:00Z"}
    with pytest.raises(ValueError):
        asff_to_event(finding)
    finding["AwsAccountId"] = "123456789012"
    finding["Types"] = "not-a-list"
    with pytest.raises(ValueError):
        asff_to_event(finding)


def test_response_action_requires_account_only_for_aws():
    base = {"action_type": "disable_aws_access_key", "target": "alice:AKIA1234567890123456",
            "rationale": "Evidence of unauthorized key use", "impact": "Dependent workloads could stop",
            "evidence_refs": ["incident:placeholder"], "idempotency_key": "unique-key-123"}
    with pytest.raises(ValidationError):
        ResponseActionCreate.model_validate(base)
    assert ResponseActionCreate.model_validate({**base, "account_id": "123456789012"}).account_id == "123456789012"


def test_incident_features_are_bounded_to_known_signals():
    case = LabeledCase(incident_id="one", account_id="123456789012", observed_at=datetime.now(UTC),
                       labels={"cloud_exposure"}, events=[{"event_type": "s3_public_exposure", "severity": "critical", "bytes_sent": 42, "secret": "ignore"}])
    values = features_for_events(case.events)
    assert set(values) == set(FEATURES)
    assert values["s3_public_exposure"] == 1
    assert values["bytes_sent"] == 42
