from __future__ import annotations

import hashlib
import io
import json
import runpy
import sys
from pathlib import Path

import pytest

from app.ml.aws_dataset import load_s3_cases, plan_s3_dataset


def _plan():
    return plan_s3_dataset(
        "s3://soc-reviewed/training/approved.jsonl",
        account_id="123456789012", allowed_bucket="soc-reviewed",
        allowed_prefix="training", max_bytes=100_000,
    )


def test_plan_is_exact_and_has_no_aws_side_effects():
    plan = _plan()
    assert plan.key == "training/approved.jsonl"
    for uri in (
        "s3://other-bucket/training/approved.jsonl",
        "s3://soc-reviewed/training2/approved.jsonl",
        "s3://soc-reviewed/training/../approved.jsonl",
        "s3://soc-reviewed/training/approved.jsonl?versionId=1",
    ):
        with pytest.raises(ValueError):
            plan_s3_dataset(
                uri, account_id="123456789012", allowed_bucket="soc-reviewed",
                allowed_prefix="training",
            )


class FakeS3:
    def __init__(self, content: bytes, *, storage_class: str = "STANDARD"):
        self.content = content
        self.storage_class = storage_class
        self.get_calls = 0

    def head_object(self, **kwargs):
        assert kwargs == {
            "Bucket": "soc-reviewed", "Key": "training/approved.jsonl",
            "ExpectedBucketOwner": "123456789012",
        }
        return {"ContentLength": len(self.content), "ETag": '"example"', "StorageClass": self.storage_class}

    def get_object(self, **kwargs):
        self.get_calls += 1
        assert kwargs["IfMatch"] == '"example"'
        return {"Body": io.BytesIO(self.content)}


class FakeSession:
    def __init__(self, s3: FakeS3, *, account_id: str = "123456789012"):
        self.s3 = s3
        self.account_id = account_id

    def client(self, name: str):
        if name == "sts":
            return self
        assert name == "s3"
        return self.s3

    def get_caller_identity(self):
        return {"Account": self.account_id}


def _cases_content() -> bytes:
    return "\n".join(json.dumps({
        "incident_id": f"case-{index}", "account_id": "123456789012",
        "observed_at": "2025-01-01T00:00:00Z", "labels": [], "events": [],
    }) for index in range(100)).encode("utf-8")


def test_s3_read_checks_identity_and_size_before_get():
    content = _cases_content()
    s3 = FakeS3(content)
    with pytest.raises(ValueError, match="credentials"):
        load_s3_cases(_plan(), aws_session=FakeSession(s3, account_id="000000000000"))
    assert s3.get_calls == 0

    oversized = FakeS3(content + b" " * 100_000)
    with pytest.raises(ValueError, match="too large"):
        load_s3_cases(_plan(), aws_session=FakeSession(oversized))
    assert oversized.get_calls == 0

    archive = FakeS3(content, storage_class="GLACIER")
    with pytest.raises(ValueError, match="S3 Standard"):
        load_s3_cases(_plan(), aws_session=FakeSession(archive))
    assert archive.get_calls == 0


def test_s3_read_parses_bounded_review_candidates():
    content = _cases_content()
    s3 = FakeS3(content)
    cases, digest = load_s3_cases(_plan(), aws_session=FakeSession(s3))
    assert len(cases) == 100
    assert cases[0].incident_id == "case-0"
    assert digest == hashlib.sha256(content).hexdigest()
    assert s3.get_calls == 1


def test_s3_read_rejects_missing_etag_or_changed_size(monkeypatch):
    content = _cases_content()
    s3 = FakeS3(content)
    monkeypatch.setattr(s3, "head_object", lambda **kwargs: {"ContentLength": len(content)})
    with pytest.raises(ValueError, match="ETag"):
        load_s3_cases(_plan(), aws_session=FakeSession(s3))
    assert s3.get_calls == 0
    monkeypatch.setattr(s3, "head_object", lambda **kwargs: {
        "ContentLength": len(content) - 1, "ETag": '"example"',
    })
    body = io.BytesIO(content)
    monkeypatch.setattr(s3, "get_object", lambda **kwargs: {"Body": body})
    with pytest.raises(ValueError, match="changed"):
        load_s3_cases(_plan(), aws_session=FakeSession(s3))
    assert body.closed


def test_cli_dry_run_never_creates_aws_session_or_trains(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("Dry run must not create clients or execute training")

    monkeypatch.setattr("boto3.Session", forbidden)
    monkeypatch.setattr("asyncio.run", forbidden)
    script = Path(__file__).resolve().parents[1] / "scripts" / "train_incident_classifier.py"
    monkeypatch.setattr(sys, "argv", [
        str(script), "--s3-uri", "s3://soc-reviewed/training/approved.jsonl",
        "--aws-account-id", "123456789012", "--aws-bucket", "soc-reviewed",
        "--aws-prefix", "training",
    ])
    runpy.run_path(str(script), run_name="__main__")
    assert "No AWS calls or training performed" in capsys.readouterr().out
