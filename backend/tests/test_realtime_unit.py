import uuid

import pytest

from app.realtime.events import RealtimePublisher
from app.realtime.tickets import RealtimeTicketStore


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, payload: str) -> None:
        self.published.append((channel, payload))

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.values[key] = value

    async def getdel(self, key: str) -> str | None:
        return self.values.pop(key, None)


@pytest.mark.anyio
async def test_realtime_publisher_routes_event_channel_and_envelopes_payload() -> None:
    redis = FakeRedis()
    publisher = RealtimePublisher(redis, channel_prefix="ai_soc:realtime")

    envelope = await publisher.publish(
        "incident.updated",
        entity_id="incident-1",
        payload={"risk_score": 91},
        version=4,
    )

    assert redis.published[0][0] == "ai_soc:realtime:incidents"
    assert envelope.type == "incident.updated"
    assert envelope.entity_id == "incident-1"
    assert envelope.version == 4
    assert '"risk_score":91' in redis.published[0][1]


@pytest.mark.anyio
async def test_realtime_ticket_is_single_use() -> None:
    redis = FakeRedis()
    store = RealtimeTicketStore(redis, key_prefix="ai_soc:realtime", ttl_seconds=60)
    user_id = uuid.uuid4()
    family_id = uuid.uuid4()

    ticket = await store.issue(user_id, family_id)

    assert await store.consume(ticket) == (user_id, family_id)
    assert await store.consume(ticket) is None