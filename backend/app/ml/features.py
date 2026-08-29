from __future__ import annotations

from collections.abc import Iterable

from app.models.event import Event

FEATURE_COLUMNS = [
    "event_type_count_window",
    "category_count_window",
    "source_ip_event_count_window",
    "username_event_count_window",
    "source_ip_distinct_usernames_window",
    "username_distinct_source_ips_window",
    "login_failure_count_window",
    "login_success_count_window",
    "privilege_change_count_window",
    "file_download_count_window",
    "api_error_count_window",
    "bytes_sent_sum_window",
    "bytes_received_sum_window",
    "is_authentication_event",
    "is_file_access_event",
    "is_privilege_change_event",
    "is_api_event",
    "is_failure_status",
]

# Isolation Forest margins are narrow; v1 exposes a scaled score so the alert
# threshold remains readable and stable while preserving model ordering.
ANOMALY_SCORE_SCALE = 8.0


def build_feature_vector(event: Event, window_events: Iterable[Event]) -> dict[str, float]:
    events = list(window_events)
    same_source = [item for item in events if event.source_ip and item.source_ip == event.source_ip]
    same_user = [item for item in events if event.username and item.username == event.username]

    values: dict[str, float] = {
        "event_type_count_window": _count(events, event_type=event.event_type),
        "category_count_window": _count(events, category=event.category),
        "source_ip_event_count_window": len(same_source),
        "username_event_count_window": len(same_user),
        "source_ip_distinct_usernames_window": len({item.username for item in same_source if item.username}),
        "username_distinct_source_ips_window": len({item.source_ip for item in same_user if item.source_ip}),
        "login_failure_count_window": _count(events, event_type="login_failure"),
        "login_success_count_window": _count(events, event_type="login_success"),
        "privilege_change_count_window": _count(events, event_type="privilege_change"),
        "file_download_count_window": sum(
            item.event_type in {"file_download", "resource_access"} for item in events
        ),
        "api_error_count_window": _count(events, event_type="api_error"),
        "bytes_sent_sum_window": sum(item.bytes_sent or 0 for item in events),
        "bytes_received_sum_window": sum(item.bytes_received or 0 for item in events),
        "is_authentication_event": event.category == "authentication",
        "is_file_access_event": event.category == "file_access",
        "is_privilege_change_event": event.event_type == "privilege_change",
        "is_api_event": event.category == "api",
        "is_failure_status": (event.status or "").lower() in {"failed", "failure", "denied", "error"},
    }
    return {column: float(values.get(column, 0)) for column in FEATURE_COLUMNS}


def _count(events: list[Event], **attributes: str) -> int:
    return sum(all(getattr(event, key) == value for key, value in attributes.items()) for event in events)
