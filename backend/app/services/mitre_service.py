from __future__ import annotations

from app.detection.registry import RuleRegistry
from app.repositories.mitre_repository import MitreRepository
from app.schemas.mitre import MitreTechniqueListResponse, MitreTechniqueResponse, RuleTechniqueResponse


class MitreService:
    def __init__(self, repository: MitreRepository, registry: RuleRegistry) -> None:
        self.repository = repository
        self.registry = registry

    async def list_techniques(self, *, tactic: str | None, search: str | None, limit: int, offset: int) -> MitreTechniqueListResponse:
        techniques, total = await self.repository.list(tactic=tactic, search=search, limit=limit, offset=offset)
        return MitreTechniqueListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[MitreTechniqueResponse.model_validate(item) for item in techniques],
        )

    async def get_technique(self, external_id: str) -> MitreTechniqueResponse | None:
        technique = await self.repository.get(external_id)
        return MitreTechniqueResponse.model_validate(technique) if technique else None

    async def get_rule_techniques(self, rule_id: str) -> RuleTechniqueResponse | None:
        if self.registry.get(rule_id) is None:
            return None
        techniques = await self.repository.get_for_rule(rule_id)
        return RuleTechniqueResponse(
            rule_id=rule_id,
            techniques=[MitreTechniqueResponse.model_validate(item) for item in techniques],
        )
