from __future__ import annotations

from dataclasses import asdict, dataclass

import joblib
import numpy as np
import pandas as pd

from app.ml.features import ANOMALY_SCORE_SCALE, FEATURE_COLUMNS
from app.models.model_registry import ModelRegistry
from app.repositories.model_registry_repository import ModelRegistryRepository


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    normal_mean_score: float
    normal_median_score: float
    abnormal_mean_score: float
    abnormal_median_score: float
    normal_below_threshold_ratio: float
    abnormal_below_threshold_ratio: float
    threshold: float
    passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_frames(
    artifact_path: str,
    normal: pd.DataFrame,
    abnormal: pd.DataFrame,
    *,
    threshold: float,
) -> EvaluationMetrics:
    artifact = joblib.load(artifact_path)
    if artifact.get("feature_columns") != FEATURE_COLUMNS:
        raise ValueError("Model artifact feature columns do not match v1")
    model = artifact["model"]
    normal_scores = model.decision_function(normal[FEATURE_COLUMNS].astype(float)) * ANOMALY_SCORE_SCALE
    abnormal_scores = model.decision_function(abnormal[FEATURE_COLUMNS].astype(float)) * ANOMALY_SCORE_SCALE
    normal_ratio = float(np.mean(normal_scores < threshold))
    abnormal_ratio = float(np.mean(abnormal_scores < threshold))
    metrics = EvaluationMetrics(
        normal_mean_score=float(np.mean(normal_scores)),
        normal_median_score=float(np.median(normal_scores)),
        abnormal_mean_score=float(np.mean(abnormal_scores)),
        abnormal_median_score=float(np.median(abnormal_scores)),
        normal_below_threshold_ratio=normal_ratio,
        abnormal_below_threshold_ratio=abnormal_ratio,
        threshold=threshold,
        passed=(
            float(np.mean(abnormal_scores)) < float(np.mean(normal_scores))
            and float(np.median(abnormal_scores)) < float(np.median(normal_scores))
            and abnormal_ratio > 0
            and normal_ratio < 0.5
        ),
    )
    return metrics


async def persist_evaluation(
    repository: ModelRegistryRepository,
    registry: ModelRegistry,
    metrics: EvaluationMetrics,
) -> None:
    await repository.update_evaluation_metrics(registry, metrics.to_dict())
