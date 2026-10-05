from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score
from sklearn.multioutput import MultiOutputClassifier

from app.core.config import Settings
from app.models.model_registry import ModelRegistry
from app.repositories.model_registry_repository import ModelRegistryRepository

LABELS = (
    "credential_compromise", "privilege_abuse", "data_exfiltration",
    "cloud_exposure", "exposed_credentials",
)
FEATURES = (
    "login_failure", "login_success", "privilege_change", "file_download",
    "api_error", "network_scan", "cloud_finding", "access_key_used",
    "s3_public_exposure", "secret_exposure", "data_exfiltration",
    "critical_findings", "high_findings", "distinct_users", "distinct_ips",
    "bytes_sent", "bytes_received",
)
MODEL_NAME = "incident_multilabel_v1"


class LabeledCase(BaseModel):
    incident_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    observed_at: datetime
    labels: set[str] = Field(default_factory=set)
    events: list[dict] = Field(default_factory=list)
    source_kind: str = "unknown"
    review_status: str = "unreviewed"


def features_for_events(events: list[dict]) -> dict[str, float]:
    kinds = [str(event.get("event_type") or "") for event in events]
    return {
        **{name: float(kinds.count(name)) for name in FEATURES[:11]},
        "critical_findings": float(sum(event.get("severity") == "critical" for event in events)),
        "high_findings": float(sum(event.get("severity") == "high" for event in events)),
        "distinct_users": float(len({event.get("username") for event in events if event.get("username")})),
        "distinct_ips": float(len({event.get("source_ip") for event in events if event.get("source_ip")})),
        "bytes_sent": float(sum(max(0, event.get("bytes_sent") or 0) for event in events)),
        "bytes_received": float(sum(max(0, event.get("bytes_received") or 0) for event in events)),
    }


def load_cases(path: Path) -> list[LabeledCase]:
    cases = [LabeledCase.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({case.incident_id for case in cases}) != len(cases):
        raise ValueError("Dataset contains repeated incident IDs")
    if any(case.labels - set(LABELS) for case in cases):
        raise ValueError("Dataset contains an unknown label")
    if len(cases) < 100:
        raise ValueError("At least 100 labeled incidents are required")
    return sorted(cases, key=lambda case: case.observed_at)


def _matrix(cases: list[LabeledCase]) -> tuple[np.ndarray, np.ndarray]:
    x = np.array([[features_for_events(case.events)[name] for name in FEATURES] for case in cases], dtype=float)
    y = np.array([[int(label in case.labels) for label in LABELS] for case in cases], dtype=int)
    return x, y


async def train_incident_classifier(
    cases: list[LabeledCase], repository: ModelRegistryRepository, settings: Settings, *, activate: bool = False,
) -> ModelRegistry:
    cases = sorted(cases, key=lambda case: case.observed_at)
    if len(cases) < 100 or len({case.incident_id for case in cases}) != len(cases):
        raise ValueError("At least 100 distinct incidents are required")
    if any(case.labels - set(LABELS) for case in cases):
        raise ValueError("Dataset contains an unknown label")
    if activate and any(case.review_status != "approved" or case.source_kind not in {"reviewed_internal", "reviewed_public_telemetry"} or not case.events for case in cases):
        raise ValueError("Activation requires approved, non-synthetic incident evidence for every case")
    cut_train, cut_validate = int(len(cases) * 0.6), int(len(cases) * 0.8)
    train, validation, test = cases[:cut_train], cases[cut_train:cut_validate], cases[cut_validate:]
    x_train, y_train = _matrix(train)
    x_validation, y_validation = _matrix(validation)
    x_test, y_test = _matrix(test)
    if any(len(set(y_train[:, i])) < 2 for i in range(len(LABELS))):
        raise ValueError("Training split needs positive and negative examples for every label")
    model = MultiOutputClassifier(RandomForestClassifier(
        n_estimators=150, min_samples_leaf=2, class_weight="balanced_subsample", random_state=42, n_jobs=1,
    ))
    model.fit(x_train, y_train)

    def probabilities(x: np.ndarray) -> np.ndarray:
        return np.column_stack([estimator.predict_proba(x)[:, 1] for estimator in model.estimators_])

    # Thresholds are selected only on validation data; the later test slice is untouched.
    validation_prob = probabilities(x_validation)
    thresholds = []
    for i in range(len(LABELS)):
        candidates = np.arange(0.2, 0.81, 0.05)
        scores = [
            (precision_score(y_validation[:, i], validation_prob[:, i] >= value, zero_division=0)
             + recall_score(y_validation[:, i], validation_prob[:, i] >= value, zero_division=0), value)
            for value in candidates
        ]
        thresholds.append(float(max(scores)[1]))
    predicted = probabilities(x_test) >= np.array(thresholds)
    metrics = {
        label: {
            "precision": float(precision_score(y_test[:, i], predicted[:, i], zero_division=0)),
            "recall": float(recall_score(y_test[:, i], predicted[:, i], zero_division=0)),
            "false_positive_rate": float(np.mean(predicted[y_test[:, i] == 0, i])) if np.any(y_test[:, i] == 0) else 1.0,
            "threshold": thresholds[i],
            "support": int(sum(y_test[:, i])),
        }
        for i, label in enumerate(LABELS)
    }
    passed = all(item["support"] >= 3 and item["precision"] >= 0.8 and item["recall"] >= 0.8 and item["false_positive_rate"] <= 0.05 for item in metrics.values())
    now = datetime.now(UTC)
    version = f"{MODEL_NAME}_{now.strftime('%Y%m%dT%H%M%S%fZ')}"
    directory = Path(settings.ml_artifact_dir)
    directory.mkdir(parents=True, exist_ok=True)
    artifact_path = directory / f"{version}.joblib"
    joblib.dump({"model": model, "features": FEATURES, "labels": LABELS, "thresholds": thresholds, "version": version}, artifact_path)
    registry = await repository.create(ModelRegistry(
        model_name=MODEL_NAME, model_version=version, algorithm="MultiOutputRandomForest",
        status="shadow", feature_version="incident-v1", artifact_path=str(artifact_path),
        trained_at=now, evaluation_metrics={"test": metrics, "passed": passed},
        training_metadata={"rows": len(cases), "train": len(train), "validation": len(validation), "test": len(test),
                           "source_kinds": sorted({case.source_kind for case in cases}),
                           "review_statuses": sorted({case.review_status for case in cases})},
    ))
    if activate:
        if not passed:
            raise ValueError("Evaluation gates failed; model remains in shadow mode")
        await repository.activate(registry, trained_at=now)
    return registry


async def classify_incident(events: list[dict], repository: ModelRegistryRepository) -> dict | None:
    registry = await repository.get_active(MODEL_NAME)
    if registry is None:
        return None
    artifact = joblib.load(registry.artifact_path)
    if artifact.get("features") != FEATURES or artifact.get("labels") != LABELS:
        raise ValueError("Incident classifier artifact contract mismatch")
    values = features_for_events(events)
    row = np.array([[values[name] for name in FEATURES]], dtype=float)
    probabilities = [float(estimator.predict_proba(row)[0, 1]) for estimator in artifact["model"].estimators_]
    return {
        "model_version": registry.model_version,
        "labels": [label for label, probability, threshold in zip(LABELS, probabilities, artifact["thresholds"]) if probability >= threshold],
        "probabilities": dict(zip(LABELS, probabilities)),
    }
