from datetime import UTC, datetime

from app.schemas.event import EventCreate
from app.services.event_normalizer import GenericJSONNormalizer


def test_generic_json_normalizer_generates_event_id_and_preserves_metadata() -> None:
    payload = EventCreate(
        timestamp=datetime(2026, 8, 24, 10, 30, tzinfo=UTC),
        source="auth-service",
        source_type="application",
        event_type="login_failure",
        category="authentication",
        username="alice",
        source_ip="192.168.1.50",
        status="failed",
        metadata={"synthetic": True},
    )

    normalized = GenericJSONNormalizer().normalize(payload)

    assert normalized.event_id.startswith("evt_")
    assert normalized.username == "alice"
    assert normalized.source_ip == "192.168.1.50"
    assert normalized.event_metadata == {"synthetic": True}
    assert normalized.raw_payload["event_type"] == "login_failure"

