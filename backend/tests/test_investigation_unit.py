from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.investigation.context import InvestigationContextBuilder
from app.investigation.provider import (
    LLMProviderDisabledError,
    OpenAIProvider,
    build_llm_provider,
)
from app.investigation.queue import InvestigationQueue
from app.investigation.validation import (
    InvestigationValidationError,
    validate_investigation_result,
)
from app.schemas.investigation import (
    EvidenceFinding,
    InvestigationContext,
    InvestigationNarrative,
    InvestigationResult,
    Recommendation,
    RiskAnalysis,
)


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs = None

    async def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp_test",
            output_parsed=InvestigationNarrative(
                executive_summary="Credential compromise detected.",
                attack_story="Failures were followed by a successful login.",
                confidence=0.9,
            ),
            usage=SimpleNamespace(input_tokens=12, output_tokens=8),
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


class FakeRedis:
    def __init__(self) -> None:
        self.items = []

    async def rpush(self, key, value):
        self.items.append((key, value))

    async def blpop(self, key, timeout):
        if not self.items:
            return None
        item_key, value = self.items.pop(0)
        return item_key, value


@pytest.mark.anyio
async def test_openai_provider_uses_structured_responses_api() -> None:
    settings = get_settings().model_copy(
        update={"llm_provider": "openai", "llm_api_key": "test-key"}
    )
    client = FakeOpenAIClient()
    provider = OpenAIProvider(settings, client=client)

    result = await provider.generate_structured(
        instructions="Investigate defensively.",
        payload={"incident_id": "inc-1"},
        response_model=InvestigationNarrative,
    )

    assert result.response_id == "resp_test"
    assert result.input_tokens == 12
    assert result.output_tokens == 8
    assert client.responses.kwargs["text_format"] is InvestigationNarrative
    assert client.responses.kwargs["store"] is False


def test_provider_factory_rejects_disabled_configuration() -> None:
    settings = get_settings().model_copy(
        update={"llm_enabled": False, "llm_provider": "disabled"}
    )

    with pytest.raises(LLMProviderDisabledError):
        build_llm_provider(settings)


@pytest.mark.anyio
async def test_investigation_queue_round_trip() -> None:
    from uuid import uuid4

    redis = FakeRedis()
    queue = InvestigationQueue(redis, queue_key="test:investigations")
    investigation_id = uuid4()

    await queue.enqueue(investigation_id)

    assert await queue.dequeue(timeout=1) == investigation_id
    assert await queue.dequeue(timeout=1) is None


def test_validation_rejects_unknown_evidence_and_risk_mismatch() -> None:
    result = InvestigationResult(
        executive_summary="Summary",
        attack_story="Story",
        confidence=0.8,
        findings=[
            EvidenceFinding(
                title="Finding",
                summary="Summary",
                severity="high",
                confidence=0.8,
                evidence_refs=["event:invented"],
            )
        ],
        evidence_gaps=[],
        risk_analysis=RiskAnalysis(
            score=90,
            severity="medium",
            rationale="Rationale",
            factors=[],
        ),
        mitre_context=[],
        recommendations=[
            Recommendation(
                title="Reset credentials",
                priority="urgent",
                rationale="Credential abuse",
                actions=["Reset the affected account"],
                evidence_refs=["event:invented"],
            )
        ],
    )

    with pytest.raises(InvestigationValidationError) as exc_info:
        validate_investigation_result(
            result,
            valid_evidence_refs={"event:real"},
        )

    assert len(exc_info.value.errors) == 3


def test_context_size_limit_truncates_untrusted_data_and_references() -> None:
    builder = InvestigationContextBuilder(
        incident_repository=SimpleNamespace(),
        event_repository=SimpleNamespace(),
        mitre_repository=SimpleNamespace(),
        max_chars=5000,
    )
    alerts = [
        {
            "ref": f"alert:{index}",
            "description": "x" * 1500,
            "evidence": {"value": "y" * 1000},
        }
        for index in range(60)
    ]
    events = [
        {"ref": f"event:{index}", "event_id": str(index)}
        for index in range(60)
    ]
    timeline = [
        {"description": "z" * 1000, "metadata": {"large": "q" * 1000}}
        for _ in range(60)
    ]
    context = InvestigationContext(
        incident={"first_seen": "start", "last_seen": "end"},
        alerts=alerts,
        events=events,
        timeline=timeline,
        techniques=[],
        valid_evidence_refs=[
            *[item["ref"] for item in alerts],
            *[item["ref"] for item in events],
        ],
    )

    truncated = builder._enforce_size(context)
    payload = truncated.model_dump(mode="json")

    assert len(json.dumps(payload, separators=(",", ":"))) <= 5000
    assert payload["incident"]["context_truncated"] is True
    retained_refs = {
        *[item["ref"] for item in payload["alerts"]],
        *[item["ref"] for item in payload["events"]],
    }
    assert set(payload["valid_evidence_refs"]) == retained_refs
