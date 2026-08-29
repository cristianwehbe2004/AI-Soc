from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import joblib
import pandas as pd
import pytest
from sklearn.ensemble import IsolationForest

from app.core.config import get_settings
from app.detection.base import DetectionContext
from app.detection.rules.ml_anomaly import MLAnomalyRule
from app.ml.evaluation import evaluate_frames
from app.ml.features import FEATURE_COLUMNS
from app.ml.inference import AnomalyScore, MLInferenceService
from app.ml.synthetic import synthetic_feature_sets
from app.models.event import Event
from app.models.model_registry import ModelRegistry


def make_event() -> Event:
    now = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    return Event(
        id=uuid4(),
        event_id="evt_ml_unit",
        timestamp=now,
        received_at=now,
        source="ml-test",
        source_type="application",
        event_type="api_error",
        category="api",
        severity="medium",
        username="alice",
        source_ip="198.51.100.1",
        status="denied",
        raw_payload={},
        event_metadata={},
        created_at=now,
    )


class StubInference:
    def __init__(self, result: AnomalyScore | None) -> None:
        self.result = result

    async def score_event(self, event, repository):
        return self.result


class StubRegistryRepository:
    def __init__(self, active=None) -> None:
        self.active = active

    async def get_active(self, model_name):
        return self.active


@pytest.mark.asyncio
async def test_ml_rule_matches_only_threshold_crossing() -> None:
    event = make_event()
    anomaly = AnomalyScore(-0.3, -0.15, "model_1", "v1", {column: 0.0 for column in FEATURE_COLUMNS})
    context = DetectionContext(object(), get_settings(), StubInference(anomaly))

    result = await MLAnomalyRule().evaluate(event, context)

    assert result is not None
    assert result.rule_id == "rule_006_ml_anomaly"
    assert result.evidence["model_version"] == "model_1"
    assert 0.60 <= result.confidence <= 0.90


@pytest.mark.asyncio
async def test_ml_rule_skips_no_model_and_non_anomaly() -> None:
    event = make_event()
    no_model = DetectionContext(object(), get_settings(), StubInference(None))
    normal = AnomalyScore(0.1, -0.15, "model_1", "v1", {})

    assert await MLAnomalyRule().evaluate(event, no_model) is None
    assert await MLAnomalyRule().evaluate(
        event,
        DetectionContext(object(), get_settings(), StubInference(normal)),
    ) is None


@pytest.mark.asyncio
async def test_inference_skips_when_no_active_model() -> None:
    service = MLInferenceService(StubRegistryRepository(), get_settings())

    assert await service.score_event(make_event(), object()) is None


def test_evaluation_separates_abnormal_from_normal(tmp_path: Path) -> None:
    normal, abnormal = synthetic_feature_sets(rows=100, seed=42)
    model = IsolationForest(contamination=0.05, random_state=42).fit(normal)
    artifact_path = tmp_path / "model.joblib"
    joblib.dump(
        {
            "model": model,
            "feature_columns": FEATURE_COLUMNS,
            "feature_version": "v1",
            "model_version": "test_model",
        },
        artifact_path,
    )

    metrics = evaluate_frames(str(artifact_path), normal, abnormal, threshold=-0.15)

    assert metrics.passed
    assert metrics.abnormal_mean_score < metrics.normal_mean_score
    assert metrics.abnormal_median_score < metrics.normal_median_score
    assert metrics.abnormal_below_threshold_ratio > 0
