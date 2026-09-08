from __future__ import annotations

import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.investigation.queue import InvestigationQueue
from app.models.investigation import Investigation
from app.repositories.incident_repository import IncidentRepository
from app.repositories.investigation_repository import InvestigationRepository
from app.schemas.investigation import (
    InvestigationListResponse,
    InvestigationResponse,
)


class InvestigationDisabledError(RuntimeError):
    pass


class InvestigationQueueError(RuntimeError):
    pass


class InvestigationService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        incident_repository: IncidentRepository,
        investigation_repository: InvestigationRepository,
        queue: InvestigationQueue,
        settings: Settings,
    ) -> None:
        self.session = session
        self.incident_repository = incident_repository
        self.investigation_repository = investigation_repository
        self.queue = queue
        self.settings = settings

    async def request_investigation(
        self,
        incident_id: uuid.UUID,
    ) -> InvestigationResponse | None:
        provider_name = self.settings.llm_provider.lower()
        if not self.settings.llm_enabled or provider_name == "disabled":
            raise InvestigationDisabledError("AI investigation is disabled")
        if provider_name != "openai":
            raise InvestigationDisabledError(
                f"Unsupported LLM provider: {self.settings.llm_provider}"
            )
        if not self.settings.llm_api_key:
            raise InvestigationDisabledError(
                "LLM_API_KEY is required for OpenAI investigations"
            )
        incident = await self.incident_repository.get(incident_id)
        if incident is None:
            return None

        context_hash = self._context_hash(incident)
        await self.investigation_repository.acquire_context_lock(
            f"investigation:{incident.id}:{context_hash}:"
            f"{self.settings.llm_prompt_version}"
        )
        investigation = await self.investigation_repository.find_for_context(
            incident_id=incident.id,
            context_hash=context_hash,
            prompt_version=self.settings.llm_prompt_version,
        )
        should_enqueue = False
        if investigation is None:
            investigation = await self.investigation_repository.create(
                Investigation(
                    incident_id=incident.id,
                    status="queued",
                    provider=self.settings.llm_provider,
                    model=self.settings.llm_model,
                    prompt_version=self.settings.llm_prompt_version,
                    context_hash=context_hash,
                    context_snapshot={},
                    validation_errors=[],
                    provider_response_ids=[],
                )
            )
            should_enqueue = True
        elif investigation.status == "failed":
            await self.investigation_repository.requeue(investigation)
            should_enqueue = True

        await self.session.commit()
        if should_enqueue:
            try:
                await self.queue.enqueue(investigation.id)
            except Exception as exc:
                await self.investigation_repository.fail(
                    investigation,
                    error=f"Unable to enqueue investigation: {exc}",
                )
                await self.session.commit()
                raise InvestigationQueueError(
                    "Unable to enqueue investigation"
                ) from exc
        return InvestigationResponse.model_validate(investigation)

    async def get_investigation(
        self,
        investigation_id: uuid.UUID,
    ) -> InvestigationResponse | None:
        investigation = await self.investigation_repository.get(investigation_id)
        if investigation is None:
            return None
        return InvestigationResponse.model_validate(investigation)

    async def list_for_incident(
        self,
        incident_id: uuid.UUID,
    ) -> InvestigationListResponse | None:
        if await self.incident_repository.get(incident_id) is None:
            return None
        investigations = await self.investigation_repository.list_for_incident(
            incident_id
        )
        return InvestigationListResponse(
            items=[
                InvestigationResponse.model_validate(investigation)
                for investigation in investigations
            ]
        )

    def _context_hash(self, incident) -> str:
        value = (
            f"{incident.id}:{incident.updated_at.isoformat()}:"
            f"{incident.risk_score}:{incident.last_seen.isoformat()}"
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
