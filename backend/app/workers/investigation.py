from __future__ import annotations

import asyncio
import logging
import uuid
import warnings
from sqlalchemy import select

warnings.filterwarnings(
    "ignore",
    message=r"The default value of `allowed_objects` will change.*",
)

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.redis import redis_client
from app.db.session import SessionLocal, engine
from app.investigation.context import InvestigationContextBuilder
from app.investigation.provider import LLMProvider, build_llm_provider
from app.investigation.queue import InvestigationQueue
from app.investigation.validation import InvestigationValidationError
from app.investigation.workflow import InvestigationWorkflow
from app.repositories.event_repository import EventRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.investigation_repository import InvestigationRepository
from app.repositories.mitre_repository import MitreRepository
from app.realtime.events import RealtimePublisher
from app.schemas.investigation import InvestigationResponse
from app.services.response_actions import QUEUE_KEY as RESPONSE_QUEUE_KEY, execute_action
from app.models.response_action import ResponseAction

logger = logging.getLogger(__name__)


async def process_investigation(
    investigation_id: uuid.UUID,
    *,
    provider: LLMProvider | None = None,
) -> bool:
    settings = get_settings()
    async with SessionLocal() as session:
        repository = InvestigationRepository(session)
        investigation = await repository.claim(investigation_id)
        if investigation is None:
            await session.rollback()
            return False
        await session.commit()
        await _publish_status(investigation, "investigation.running", settings)

        owns_provider = provider is None
        active_provider = None
        try:
            active_provider = provider or build_llm_provider(settings)
            workflow = InvestigationWorkflow(
                context_builder=InvestigationContextBuilder(
                    incident_repository=IncidentRepository(session),
                    event_repository=EventRepository(session),
                    mitre_repository=MitreRepository(session),
                    max_chars=settings.llm_context_max_chars,
                ),
                investigation_repository=repository,
                provider=active_provider,
                session=session,
            )
            await workflow.run(
                investigation_id=investigation.id,
                incident_id=investigation.incident_id,
            )
            await session.commit()
            completed = await repository.get(investigation.id)
            if completed is not None:
                await _publish_status(completed, "investigation.completed", settings)
            return True
        except Exception as exc:
            await session.rollback()
            failed = await repository.get(investigation_id)
            if failed is not None:
                validation_errors = (
                    exc.errors
                    if isinstance(exc, InvestigationValidationError)
                    else []
                )
                await repository.fail(
                    failed,
                    error=str(exc),
                    validation_errors=validation_errors,
                )
                await session.commit()
                await _publish_status(failed, "investigation.failed", settings)
            logger.exception(
                "Investigation processing failed",
                extra={"investigation_id": str(investigation_id)},
            )
            return False
        finally:
            if owns_provider and active_provider is not None:
                await active_provider.aclose()


async def _publish_status(investigation, event_type: str, settings) -> None:
    try:
        await RealtimePublisher(
            redis_client,
            channel_prefix=settings.realtime_redis_channel_prefix,
        ).publish(
            event_type,
            entity_id=str(investigation.id),
            payload={"incident_id": str(investigation.incident_id), "status": investigation.status},
            version=int(investigation.updated_at.timestamp() * 1_000_000),
        )
    except Exception:
        logger.exception("Realtime investigation publication failed", extra={"investigation_id": str(investigation.id)})


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings)
    queue = InvestigationQueue(
        redis_client,
        queue_key=settings.investigation_queue_key,
    )
    logger.info("Investigation worker started")
    last_recovery = 0.0
    while True:
        now = asyncio.get_running_loop().time()
        if now - last_recovery >= 60:
            async with SessionLocal() as session:
                pending = (await session.scalars(select(ResponseAction.id).where(ResponseAction.status == "approved").limit(100))).all()
            for action_id in pending:
                await execute_action(action_id, SessionLocal, settings)
            last_recovery = now
        response_item = await redis_client.lpop(RESPONSE_QUEUE_KEY)
        if response_item is not None:
            await execute_action(uuid.UUID(response_item.decode() if isinstance(response_item, bytes) else response_item), SessionLocal, settings)
            continue
        investigation_id = await queue.dequeue(
            timeout=settings.investigation_worker_block_seconds
        )
        if investigation_id is not None:
            await process_investigation(investigation_id)


async def main() -> None:
    try:
        await run_worker()
    finally:
        await redis_client.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
