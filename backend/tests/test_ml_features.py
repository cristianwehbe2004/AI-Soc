from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.ml.dataset import build_dataset
from app.ml.features import FEATURE_COLUMNS, build_feature_vector
from app.models.event import Event


def make_event(index: int, timestamp: datetime, **overrides) -> Event:
    return Event(
        event_id=f"ml_feature_{index}",
        timestamp=timestamp,
        source="ml-test",
        source_type="application",
        event_type=overrides.get("event_type", "api_request"),
        category=overrides.get("category", "api"),
        username=overrides.get("username"),
        source_ip=overrides.get("source_ip"),
        status=overrides.get("status"),
        bytes_sent=overrides.get("bytes_sent"),
        bytes_received=overrides.get("bytes_received"),
        raw_payload={},
        event_metadata={},
        created_at=timestamp,
    )


def test_feature_vector_has_fixed_order_and_zero_fills_missing_values() -> None:
    now = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    event = make_event(1, now)

    features = build_feature_vector(event, [event])

    assert list(features) == FEATURE_COLUMNS
    assert all(isinstance(value, float) for value in features.values())
    assert features["source_ip_event_count_window"] == 0
    assert features["bytes_received_sum_window"] == 0
    assert features["is_api_event"] == 1


def test_dataset_aggregation_uses_fixed_rolling_window() -> None:
    now = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    events = [
        make_event(1, now - timedelta(seconds=301), source_ip="192.0.2.1"),
        make_event(2, now - timedelta(seconds=10), source_ip="192.0.2.1"),
        make_event(3, now, source_ip="192.0.2.1", bytes_received=500),
    ]

    frame = build_dataset(events, window_seconds=300)

    assert list(frame.columns) == FEATURE_COLUMNS
    assert frame.iloc[-1]["event_type_count_window"] == 2
    assert frame.iloc[-1]["source_ip_event_count_window"] == 2
    assert frame.iloc[-1]["bytes_received_sum_window"] == 500
