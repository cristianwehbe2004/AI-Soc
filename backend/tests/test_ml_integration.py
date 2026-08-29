from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ml.dataset import generate_dataset
from app.ml.features import FEATURE_COLUMNS
from app.ml.synthetic import synthetic_feature_sets
from app.ml.training import train_model
from app.models.event import Event
from app.repositories.alert_repository import AlertRepository
from app.repositories.event_repository import EventRepository
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.schemas.event import EventBulkCreate, EventCreate
from app.services.event_service import EventService


def training_settings(tmp_path: Path):
    return get_settings().model_copy(
        update={
            "ml_artifact_dir": str(tmp_path),
            "ml_min_training_rows": 50,
            "ml_anomaly_alert_threshold": -0.15,
        }
    )


@pytest.mark.asyncio
async def test_dataset_generation_from_stored_events_has_expected_rows() -> None:
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        repository = EventRepository(session)
        for index in range(5):
            await repository.create(
                Event(
                    event_id=f"dataset_{index}",
                    timestamp=now - timedelta(seconds=5 - index),
                    source="dataset-test",
                    source_type="application",
                    event_type="api_request",
                    category="api",
                    source_ip="192.0.2.10",
                    username="alice",
                    status="success",
                    raw_payload={},
                    event_metadata={},
                )
            )
        await session.commit()
        frame = await generate_dataset(
            repository,
            end_time=now,
            lookback_days=1,
            window_seconds=300,
        )

    assert len(frame) == 5
    assert list(frame.columns) == FEATURE_COLUMNS


@pytest.mark.asyncio
async def test_training_saves_artifact_and_replaces_active_model(tmp_path: Path) -> None:
    settings = training_settings(tmp_path)
    normal, _ = synthetic_feature_sets(rows=100)
    async with SessionLocal() as session:
        repository = ModelRegistryRepository(session)
        first = await train_model(
            normal,
            repository=repository,
            settings=settings,
            trained_at=datetime(2026, 8, 25, 10, 0, tzinfo=UTC),
        )
        second = await train_model(
            normal,
            repository=repository,
            settings=settings,
            trained_at=datetime(2026, 8, 25, 10, 1, tzinfo=UTC),
        )
        await session.commit()
        active = await repository.get_active(settings.ml_model_name)

    assert Path(first.artifact_path).exists()
    assert Path(second.artifact_path).exists()
    assert first.status == "inactive"
    assert active is not None
    assert active.id == second.id


@pytest.mark.asyncio
async def test_abnormal_bulk_ingest_creates_ml_alert_and_reuses_model(tmp_path: Path, monkeypatch) -> None:
    settings = training_settings(tmp_path)
    normal, _ = synthetic_feature_sets(rows=100)
    async with SessionLocal() as session:
        await train_model(normal, repository=ModelRegistryRepository(session), settings=settings)
        await session.commit()

    monkeypatch.setattr("app.services.event_service.get_settings", lambda: settings)
    from app.ml import inference as inference_module

    original_load = inference_module.joblib.load
    load_calls = 0

    def counting_load(path):
        nonlocal load_calls
        load_calls += 1
        return original_load(path)

    monkeypatch.setattr(inference_module.joblib, "load", counting_load)
    now = datetime(2026, 8, 25, 14, 0, tzinfo=UTC)
    events = [
        EventCreate(
            event_id=f"abnormal_{index}",
            timestamp=now + timedelta(seconds=index),
            source="compromised-host",
            source_type="application",
            event_type="api_error",
            category="api",
            severity="high",
            username=f"target-{index % 15}",
            source_ip="198.51.100.200",
            status="denied",
            bytes_sent=100_000,
            bytes_received=5_000_000,
            metadata={"synthetic": True, "scenario": "abnormal-telemetry"},
        )
        for index in range(50)
    ]

    async with SessionLocal() as session:
        service = EventService(session)
        await service.create_events_bulk(EventBulkCreate(events=events))
        loaded_id = service.ml_inference_service._registry_id
        loaded_artifact = service.ml_inference_service._artifact

    async with SessionLocal() as session:
        alerts = await AlertRepository(session).list_all()

    ml_alerts = [alert for alert in alerts if alert.rule_id == "rule_006_ml_anomaly"]
    assert ml_alerts
    assert loaded_id is not None
    assert loaded_artifact is not None
    assert load_calls == 1
    assert all("anomaly_score" in alert.evidence for alert in ml_alerts)
