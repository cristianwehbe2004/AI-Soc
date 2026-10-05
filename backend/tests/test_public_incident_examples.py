import pytest
from pathlib import Path
from runpy import run_path
import json

project_metadata = run_path(str(Path(__file__).resolve().parents[1] / "scripts" / "collect_public_incident_examples.py"))["project_metadata"]


def test_projects_safe_metadata_only():
    body = b'''title: Example public key exposure
id: example-1
description: Key AKIA1234567890123456 was used from 192.0.2.1
platform: [AWS]
tags: [Credential Access]
attack_mappings:
  - technique: T1078
simulation:
  adversary_view: "secret command transcript"
files:
  - link: https://example.com/huge.zip
'''
    record = project_metadata("datasets/atomic/_metadata/example-1.yaml", body)
    assert record["train_ready"] is False
    assert record["attack_techniques"] == ["T1078"]
    assert "AKIA1234567890123456" not in str(record)
    assert "192.0.2.1" not in str(record)
    assert "secret command transcript" not in str(record)
    assert "huge.zip" not in str(record)


def test_rejects_non_metadata_path():
    with pytest.raises(ValueError):
        project_metadata("datasets/atomic/aws/raw.zip", b"test")


def test_checked_in_corpus_is_provenance_only():
    path = Path(__file__).resolve().parents[1] / "data" / "public_incident_examples.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 113
    assert len({record["scenario_id"] for record in records}) == len(records)
    assert all(record["train_ready"] is False and record["review_status"] == "unreviewed" for record in records)
    assert all(record["source_url"].startswith("https://github.com/OTRF/Security-Datasets/blob/") for record in records)
