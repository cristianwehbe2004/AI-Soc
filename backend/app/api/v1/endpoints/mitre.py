from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.detection import build_rule_registry
from app.repositories.mitre_repository import MitreRepository
from app.schemas.mitre import (
    MitreTechniqueListResponse,
    MitreTechniqueResponse,
    RuleTechniqueResponse,
)
from app.services.mitre_service import MitreService
from app.security.dependencies import require_permission
from app.security.permissions import Permission

router = APIRouter(
    prefix="/mitre",
    dependencies=[Depends(require_permission(Permission.SOC_READ))],
)


def get_mitre_service(session: AsyncSession = Depends(get_db_session)) -> MitreService:
    return MitreService(MitreRepository(session), build_rule_registry())


@router.get("/techniques", response_model=MitreTechniqueListResponse)
async def list_techniques(
    tactic: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: MitreService = Depends(get_mitre_service),
) -> MitreTechniqueListResponse:
    return await service.list_techniques(tactic=tactic, search=search, limit=limit, offset=offset)


@router.get("/rules/{rule_id}/techniques", response_model=RuleTechniqueResponse)
async def get_rule_techniques(
    rule_id: str,
    service: MitreService = Depends(get_mitre_service),
) -> RuleTechniqueResponse:
    result = await service.get_rule_techniques(rule_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection rule not found")
    return result


@router.get("/techniques/{external_id}", response_model=MitreTechniqueResponse)
async def get_technique(
    external_id: str,
    service: MitreService = Depends(get_mitre_service),
) -> MitreTechniqueResponse:
    technique = await service.get_technique(external_id)
    if technique is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MITRE technique not found")
    return technique
