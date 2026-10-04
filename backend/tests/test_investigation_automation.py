from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.investigation.automation import AutomaticInvestigationDispatcher, AutomaticInvestigationPolicy


class FakeRedis:
    def __init__(self) -> None:
        self.values: set[str] = set()
        self.deleted: list[str] = []

    async def set(self, key: str, value: str, *, ex: int, nx: bool) -> bool:
        if nx and key in self.values:
            return False
        self.values.add(key)
        return True

    async def delete(self, key: str) -> None:
        self.values.discard(key)
        self.deleted.append(key)


def incident(*, severity: str, status: str = "open"):
    return SimpleNamespace(id=uuid4(), severity=severity, status=status)


def test_automatic_policy_is_disabled_by_default() -> None:
    policy = AutomaticInvestigationPolicy(get_settings().model_copy())

    assert policy.should_trigger(incident(severity="critical")) is False


def test_automatic_policy_requires_configured_severity_and_open_status() -> None:
    settings = get_settings().model_copy(
        update={
            "automatic_investigations_enabled": True,
            "automatic_investigation_min_severity": "high",
        }
    )
    policy = AutomaticInvestigationPolicy(settings)

    assert policy.should_trigger(incident(severity="medium")) is False
    assert policy.should_trigger(incident(severity="high")) is True
    assert policy.should_trigger(incident(severity="critical", status="resolved")) is False


@pytest.mark.anyio
async def test_dispatcher_cooldown_deduplicates_incident_requests() -> None:
    settings = get_settings().model_copy(
        update={
            "automatic_investigations_enabled": True,
            "automatic_investigation_min_severity": "high",
        }
    )
    redis = FakeRedis()
    dispatcher = AutomaticInvestigationDispatcher(None, redis, settings)
    requested = []

    async def fake_request(incident_id):
        requested.append(incident_id)

    dispatcher.service.request_investigation = fake_request
    case = incident(severity="critical")

    await dispatcher.dispatch([case, case])

    assert requested == [case.id]