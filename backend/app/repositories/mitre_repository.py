from __future__ import annotations

from sqlalchemy import cast, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.mitre.catalog import CORE_RULE_MAPPINGS, CORE_TECHNIQUES
from app.models.mitre import MitreTechnique, RuleTechniqueMapping


class MitreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        tactic: str | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[MitreTechnique], int]:
        query = select(MitreTechnique)
        count_query = select(func.count()).select_from(MitreTechnique)
        if tactic:
            tactic_filter = MitreTechnique.tactics.op("@>")(cast([tactic], JSONB))
            query = query.where(tactic_filter)
            count_query = count_query.where(tactic_filter)
        if search:
            pattern = f"%{search}%"
            predicate = or_(
                MitreTechnique.external_id.ilike(pattern),
                MitreTechnique.name.ilike(pattern),
            )
            query = query.where(predicate)
            count_query = count_query.where(predicate)
        result = await self.session.execute(
            query.order_by(MitreTechnique.external_id).limit(limit).offset(offset)
        )
        total = await self.session.execute(count_query)
        return list(result.scalars().all()), int(total.scalar_one())

    async def get(self, external_id: str) -> MitreTechnique | None:
        return await self.session.get(MitreTechnique, external_id.upper())

    async def get_for_rule(self, rule_id: str) -> list[MitreTechnique]:
        return await self.get_for_rules([rule_id])

    async def get_for_rules(self, rule_ids: list[str]) -> list[MitreTechnique]:
        if not rule_ids:
            return []
        result = await self.session.execute(
            select(MitreTechnique)
            .join(
                RuleTechniqueMapping,
                RuleTechniqueMapping.technique_external_id
                == MitreTechnique.external_id,
            )
            .where(RuleTechniqueMapping.rule_id.in_(rule_ids))
            .distinct()
            .order_by(MitreTechnique.external_id)
        )
        return list(result.scalars().all())

    async def seed_core_catalog(self) -> None:
        technique_ids = [item["external_id"] for item in CORE_TECHNIQUES]
        existing = set(
            (
                await self.session.execute(
                    select(MitreTechnique.external_id).where(
                        MitreTechnique.external_id.in_(technique_ids)
                    )
                )
            ).scalars()
        )
        self.session.add_all(
            [
                MitreTechnique(**item)
                for item in CORE_TECHNIQUES
                if item["external_id"] not in existing
            ]
        )
        await self.session.flush()
        existing_mappings = set(
            (
                await self.session.execute(
                    select(
                        RuleTechniqueMapping.rule_id,
                        RuleTechniqueMapping.technique_external_id,
                    )
                )
            ).all()
        )
        self.session.add_all(
            [
                RuleTechniqueMapping(
                    rule_id=rule_id,
                    technique_external_id=technique_id,
                )
                for rule_id, technique_id in CORE_RULE_MAPPINGS
                if (rule_id, technique_id) not in existing_mappings
            ]
        )
        await self.session.flush()
