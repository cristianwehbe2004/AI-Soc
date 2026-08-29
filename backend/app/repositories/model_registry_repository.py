from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_registry import ModelRegistry


class ModelRegistryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, model: ModelRegistry) -> ModelRegistry:
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def get_active(self, model_name: str) -> ModelRegistry | None:
        result = await self.session.execute(
            select(ModelRegistry)
            .where(ModelRegistry.model_name == model_name, ModelRegistry.status == "active")
            .order_by(ModelRegistry.trained_at.desc(), ModelRegistry.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def activate(self, model: ModelRegistry, *, trained_at: datetime) -> ModelRegistry:
        await self.session.execute(
            update(ModelRegistry)
            .where(
                ModelRegistry.model_name == model.model_name,
                ModelRegistry.status == "active",
                ModelRegistry.id != model.id,
            )
            .values(status="inactive")
        )
        model.status = "active"
        model.trained_at = trained_at
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_evaluation_metrics(self, model: ModelRegistry, metrics: dict) -> None:
        model.evaluation_metrics = metrics
        await self.session.flush()
