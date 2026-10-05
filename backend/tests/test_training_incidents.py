from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ml.incident_classifier import LabeledCase, train_incident_classifier
from app.ml.training_examples import load_training_cases, make_lab_incidents, seed_training_incidents
from app.models.incident import Incident
from app.models.training_incident import TrainingIncident


def test_lab_examples_are_balanced_and_not_operational():
    rows = make_lab_incidents()
    assert len(rows) == 180
    assert len({row.scenario_id for row in rows}) == 180
    assert sum(not row.labels for row in rows) == 30
    assert {row.labels[0] for row in rows if row.labels} == {
        "credential_compromise", "privilege_abuse", "data_exfiltration", "cloud_exposure", "exposed_credentials"
    }
    assert all(row.source_kind == "lab_synthetic" and row.review_status == "synthetic" for row in rows)


@pytest.mark.anyio
async def test_seed_is_idempotent_and_does_not_create_live_incidents():
    path = Path(__file__).resolve().parents[1] / "data" / "public_incident_examples.jsonl"
    async with SessionLocal() as session:
        before = await session.scalar(select(func.count()).select_from(Incident))
        await seed_training_incidents(session, path)
        await session.commit()
        assert await session.scalar(select(func.count()).select_from(TrainingIncident)) == 293
        assert await session.scalar(select(func.count()).select_from(Incident)) == before
        inserted = await seed_training_incidents(session, path)
        assert inserted == {"public_simulation_metadata": 0, "lab_synthetic": 0}
        cases = await load_training_cases(session, lab_shadow=True)
        assert len(cases) == 180
        assert await load_training_cases(session) == []


@pytest.mark.anyio
async def test_synthetic_cases_cannot_be_activated():
    async with SessionLocal() as session:
        cases = await load_training_cases(session, lab_shadow=True)
        if not cases:
            rows = make_lab_incidents()
            cases = [LabeledCase(
                incident_id=row.scenario_id, account_id=row.account_id, observed_at=row.observed_at,
                labels=set(row.labels), events=row.events, source_kind=row.source_kind, review_status=row.review_status,
            ) for row in rows]
        with pytest.raises(ValueError, match="approved, non-synthetic"):
            await train_incident_classifier(cases, None, get_settings(), activate=True)
