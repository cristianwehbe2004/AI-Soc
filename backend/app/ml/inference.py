from __future__ import annotations

from dataclasses import dataclass

import joblib
import pandas as pd

from app.core.config import Settings
from app.ml.aggregation import event_window
from app.ml.features import ANOMALY_SCORE_SCALE, FEATURE_COLUMNS, build_feature_vector
from app.models.event import Event
from app.repositories.event_repository import EventRepository
from app.repositories.model_registry_repository import ModelRegistryRepository


@dataclass(frozen=True, slots=True)
class AnomalyScore:
    score: float
    threshold: float
    model_version: str
    feature_version: str
    features: dict[str, float]

    @property
    def is_anomaly(self) -> bool:
        return self.score < self.threshold


class MLInferenceService:
    def __init__(self, repository: ModelRegistryRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings
        self._registry_id = None
        self._artifact: dict | None = None

    async def score_event(
        self,
        event: Event,
        event_repository: EventRepository,
    ) -> AnomalyScore | None:
        if not self.settings.ml_enabled:
            return None
        registry = await self.repository.get_active(self.settings.ml_model_name)
        if registry is None:
            return None
        artifact = self._load_artifact(registry.id, registry.artifact_path)
        feature_columns = artifact.get("feature_columns")
        if feature_columns != FEATURE_COLUMNS or artifact.get("feature_version") != registry.feature_version:
            raise ValueError("Active ML artifact does not match the configured v1 feature contract")

        events = await event_window(
            event_repository,
            event,
            window_seconds=self.settings.ml_aggregation_window_seconds,
        )
        features = build_feature_vector(event, events)
        frame = pd.DataFrame([[features[column] for column in feature_columns]], columns=feature_columns)
        score = float(artifact["model"].decision_function(frame)[0] * ANOMALY_SCORE_SCALE)
        return AnomalyScore(
            score=score,
            threshold=self.settings.ml_anomaly_alert_threshold,
            model_version=registry.model_version,
            feature_version=registry.feature_version,
            features=features,
        )

    def _load_artifact(self, registry_id, artifact_path: str) -> dict:
        if self._registry_id != registry_id or self._artifact is None:
            artifact = joblib.load(artifact_path)
            if not isinstance(artifact, dict) or "model" not in artifact:
                raise ValueError("Active ML artifact has an invalid format")
            self._artifact = artifact
            self._registry_id = registry_id
        return self._artifact
