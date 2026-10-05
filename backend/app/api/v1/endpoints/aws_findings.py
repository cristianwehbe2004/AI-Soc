from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.security.dependencies import ServicePrincipal, require_event_ingest_key
from app.schemas.event import EventBulkCreate, EventBulkIngestResponse
from app.services.aws_finding_adapter import ASFFBatch, asff_to_event
from app.services.event_service import EventService
from app.api.v1.endpoints.events import get_event_service
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService

router = APIRouter(prefix="/aws/findings", tags=["aws-findings"])


def is_active_finding(finding: dict) -> bool:
    workflow = finding.get("Workflow") or {}
    if not isinstance(workflow, dict):
        raise ValueError("Finding Workflow must be an object")
    return (
        str(finding.get("RecordState") or "ACTIVE").upper() == "ACTIVE"
        and str(workflow.get("Status") or "NEW").upper() not in {"RESOLVED", "SUPPRESSED"}
    )


@router.post("/bulk", response_model=EventBulkIngestResponse)
async def ingest_asff(
    body: ASFFBatch,
    request: Request,
    principal: Annotated[ServicePrincipal, Depends(require_event_ingest_key)],
    service: EventService = Depends(get_event_service),
) -> EventBulkIngestResponse:
    try:
        active_findings = [finding for finding in body.findings if is_active_finding(finding)]
        events = [asff_to_event(finding) for finding in active_findings]
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    seen: set[str] = set()
    unseen = []
    for event in events:
        if event.event_id in seen:
            continue
        seen.add(event.event_id)
        if await service.repository.get_by_event_id(event.event_id) is None:
            unseen.append(event)
    if unseen:
        result = await service.create_events_bulk(EventBulkCreate(events=unseen))
    else:
        result = EventBulkIngestResponse(accepted=True, count=0, events=[])
    await AuditService(AuditRepository(service.session)).record(
        request=request,
        action="aws.findings.ingest",
        outcome="success",
        actor_type="api_key",
        actor_id=principal.id,
        actor_label=principal.name,
        resource_type="aws_finding",
        details={"accepted": result.count, "duplicates": len(events) - result.count, "inactive_skipped": len(body.findings) - len(events)},
    )
    await service.session.commit()
    return result
