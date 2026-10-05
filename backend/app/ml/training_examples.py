"""Training-only reference and lab fixtures; never operational incidents."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.incident_classifier import LabeledCase
from app.models.training_incident import TrainingIncident

LAB_VERSION = "lab-v1"
LAB_START = datetime(2024, 1, 1, tzinfo=UTC)
LAB_CLASSES = (
    ("benign", None),
    ("credential_compromise", "credential_compromise"),
    ("privilege_abuse", "privilege_abuse"),
    ("data_exfiltration", "data_exfiltration"),
    ("cloud_exposure", "cloud_exposure"),
    ("exposed_credentials", "exposed_credentials"),
)


def lab_events(kind: str, sequence: int) -> list[dict]:
    """Create minimal, synthetic normalized event summaries, never raw logs."""
    actor = f"lab-user-{sequence % 11}"
    source_ip = f"192.0.2.{1 + sequence % 200}"
    common = {"username": actor, "source_ip": source_ip}
    if kind == "benign":
        return [{"event_type": "login_success", "severity": "low", **common},
                {"event_type": "api_request", "severity": "low", **common}]
    if kind == "credential_compromise":
        return ([{"event_type": "login_failure", "severity": "medium", **common} for _ in range(3 + sequence % 4)]
                + [{"event_type": "login_success", "severity": "high", **common}])
    if kind == "privilege_abuse":
        return [{"event_type": "login_success", "severity": "medium", **common},
                {"event_type": "privilege_change", "severity": "high", **common}]
    if kind == "data_exfiltration":
        return [{"event_type": "file_download", "severity": "medium", "bytes_received": 100_000 + sequence * 1000, **common},
                {"event_type": "data_exfiltration", "severity": "critical", "bytes_sent": 2_000_000 + sequence * 10000, **common}]
    if kind == "cloud_exposure":
        return [{"event_type": "s3_public_exposure", "severity": "high", **common},
                {"event_type": "cloud_finding", "severity": "high", **common}]
    if kind == "exposed_credentials":
        return [{"event_type": "secret_exposure", "severity": "critical", **common},
                {"event_type": "cloud_finding", "severity": "medium", **common}]
    raise ValueError(f"Unknown lab class: {kind}")


def make_lab_incidents(per_class: int = 30) -> list[TrainingIncident]:
    if not 20 <= per_class <= 100:
        raise ValueError("Lab examples per class must be 20..100")
    rows = []
    for sequence in range(per_class):
        for offset, (kind, label) in enumerate(LAB_CLASSES):
            ordinal = sequence * len(LAB_CLASSES) + offset
            scenario_id = f"{LAB_VERSION}-{ordinal:04d}"
            rows.append(TrainingIncident(
                id=uuid.uuid5(uuid.NAMESPACE_URL, f"ai-soc/{scenario_id}"),
                scenario_id=scenario_id,
                title=f"Synthetic lab example: {kind.replace('_', ' ')}",
                account_id="lab-local",
                observed_at=LAB_START + timedelta(minutes=ordinal),
                source_kind="lab_synthetic",
                review_status="synthetic",
                labels=[label] if label else [],
                events=lab_events(kind, ordinal),
                source_ref=None,
            ))
    return rows


def load_public_references(path: Path) -> list[TrainingIncident]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for record in records:
        if record.get("train_ready") is not False or record.get("review_status") != "unreviewed":
            raise ValueError("Public research corpus must be unreviewed and not train-ready")
        scenario_id = f"otrf:{record['scenario_id']}"
        rows.append(TrainingIncident(
            id=uuid.uuid5(uuid.NAMESPACE_URL, f"ai-soc/{scenario_id}"),
            scenario_id=scenario_id,
            title=record["title"][:255],
            account_id="public-reference",
            observed_at=None,
            source_kind="public_simulation_metadata",
            review_status="unreviewed",
            labels=[],
            events=[],
            source_ref=record["source_url"],
        ))
    return rows


async def seed_training_incidents(session: AsyncSession, public_path: Path, *, per_class: int = 30) -> dict[str, int]:
    candidates = load_public_references(public_path) + make_lab_incidents(per_class)
    existing = set((await session.scalars(select(TrainingIncident.scenario_id))).all())
    inserted = {"public_simulation_metadata": 0, "lab_synthetic": 0}
    for row in candidates:
        if row.scenario_id in existing:
            continue
        session.add(row)
        inserted[row.source_kind] += 1
    await session.flush()
    return inserted


async def load_training_cases(session: AsyncSession, *, lab_shadow: bool = False) -> list[LabeledCase]:
    allowed = ["lab_synthetic"] if lab_shadow else ["reviewed_internal", "reviewed_public_telemetry"]
    rows = (await session.scalars(
        select(TrainingIncident).where(TrainingIncident.source_kind.in_(allowed)).order_by(TrainingIncident.observed_at)
    )).all()
    return [LabeledCase(
        incident_id=row.scenario_id, account_id=row.account_id, observed_at=row.observed_at,
        labels=set(row.labels), events=row.events, source_kind=row.source_kind, review_status=row.review_status,
    ) for row in rows if row.observed_at is not None and row.events and (lab_shadow or row.review_status == "approved")]
