from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.core.config import Settings
from app.ml.features import ANOMALY_SCORE_SCALE, FEATURE_COLUMNS
from app.models.model_registry import ModelRegistry
from app.repositories.model_registry_repository import ModelRegistryRepository


def make_model_version(model_name: str, trained_at: datetime) -> str:
    timestamp = trained_at.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{model_name}_{timestamp}"


async def train_model(
    frame: pd.DataFrame,
    *,
    repository: ModelRegistryRepository,
    settings: Settings,
    trained_at: datetime | None = None,
) -> ModelRegistry:
    if len(frame) < settings.ml_min_training_rows:
        raise ValueError(f"Training requires at least {settings.ml_min_training_rows} rows; received {len(frame)}")
    missing = [column for column in FEATURE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Training dataset is missing feature columns: {', '.join(missing)}")

    trained_at = trained_at or datetime.now(UTC)
    version = make_model_version(settings.ml_model_name, trained_at)
    artifact_dir = Path(settings.ml_artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{version}.joblib"
    registry = await repository.create(
        ModelRegistry(
            model_name=settings.ml_model_name,
            model_version=version,
            algorithm="IsolationForest",
            status="training",
            feature_version=settings.ml_feature_version,
            artifact_path=str(artifact_path),
            trained_at=None,
            evaluation_metrics={},
            training_metadata={
                "row_count": len(frame),
                "feature_columns": FEATURE_COLUMNS,
                "contamination": settings.ml_isolation_forest_contamination,
                "random_state": settings.ml_isolation_forest_random_state,
                "anomaly_score_scale": ANOMALY_SCORE_SCALE,
            },
        )
    )

    try:
        model = IsolationForest(
            contamination=settings.ml_isolation_forest_contamination,
            random_state=settings.ml_isolation_forest_random_state,
        )
        model.fit(frame[FEATURE_COLUMNS].astype(float))
        joblib.dump(
            {
                "model": model,
                "feature_columns": FEATURE_COLUMNS,
                "feature_version": settings.ml_feature_version,
                "model_version": version,
            },
            artifact_path,
        )
        return await repository.activate(registry, trained_at=trained_at)
    except Exception:
        registry.status = "failed"
        await repository.session.flush()
        raise
