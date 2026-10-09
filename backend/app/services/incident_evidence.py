from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident_evidence import IncidentEvidence
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident_evidence import IncidentEvidenceCreate

MAX_EVIDENCE_PER_INCIDENT = 200
SECRET_PATTERNS = (
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"(?i)\b(?:password|secret|token|api[_-]?key)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
)


class IncidentEvidenceError(ValueError):
    pass


def redact_secrets(value: str) -> tuple[str, bool]:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted, redacted != value


async def list_evidence(session: AsyncSession, incident_id: uuid.UUID) -> list[IncidentEvidence]:
    result = await session.scalars(
        select(IncidentEvidence).where(IncidentEvidence.incident_id == incident_id)
        .order_by(IncidentEvidence.created_at, IncidentEvidence.id).limit(MAX_EVIDENCE_PER_INCIDENT)
    )
    return list(result)


async def add_evidence(session: AsyncSession, incident_id: uuid.UUID, actor_id: uuid.UUID, payload: IncidentEvidenceCreate) -> IncidentEvidence:
    if await IncidentRepository(session).get(incident_id) is None:
        raise IncidentEvidenceError("Incident not found")
    count = await session.scalar(select(func.count()).select_from(IncidentEvidence).where(IncidentEvidence.incident_id == incident_id))
    if (count or 0) >= MAX_EVIDENCE_PER_INCIDENT:
        raise IncidentEvidenceError("Incident evidence limit reached")
    source, source_redacted = redact_secrets(payload.source)
    summary, summary_redacted = redact_secrets(payload.summary)
    row = IncidentEvidence(
        incident_id=incident_id,
        submitted_by=actor_id,
        kind=payload.kind,
        source=source,
        summary=summary,
        network=payload.network.model_dump(mode="json") if payload.network else None,
        observed_at=payload.observed_at,
        sensitive_redacted=source_redacted or summary_redacted,
    )
    session.add(row)
    await session.flush()
    return row
