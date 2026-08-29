from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.features import FEATURE_COLUMNS


def synthetic_feature_sets(*, rows: int = 100, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    normal_rows = []
    abnormal_rows = []
    for _ in range(rows):
        normal_rows.append(
            _row(
                event_count=rng.integers(1, 5),
                identity_count=rng.integers(1, 4),
                distinct_users=1,
                failures=rng.integers(0, 2),
                api_errors=rng.integers(0, 2),
                bytes_received=rng.integers(500, 25_000),
            )
        )
        abnormal_rows.append(
            _row(
                event_count=rng.integers(45, 90),
                identity_count=rng.integers(35, 80),
                distinct_users=rng.integers(10, 30),
                failures=rng.integers(15, 40),
                api_errors=rng.integers(20, 60),
                bytes_received=rng.integers(5_000_000, 30_000_000),
                privilege_changes=rng.integers(2, 8),
                downloads=rng.integers(5, 20),
            )
        )
    return (
        pd.DataFrame(normal_rows, columns=FEATURE_COLUMNS),
        pd.DataFrame(abnormal_rows, columns=FEATURE_COLUMNS),
    )


def _row(
    *,
    event_count: int,
    identity_count: int,
    distinct_users: int,
    failures: int,
    api_errors: int,
    bytes_received: int,
    privilege_changes: int = 0,
    downloads: int = 0,
) -> dict[str, float]:
    return {
        "event_type_count_window": event_count,
        "category_count_window": event_count,
        "source_ip_event_count_window": identity_count,
        "username_event_count_window": max(1, identity_count // max(1, distinct_users)),
        "source_ip_distinct_usernames_window": distinct_users,
        "username_distinct_source_ips_window": 1,
        "login_failure_count_window": failures,
        "login_success_count_window": max(0, event_count - failures - api_errors),
        "privilege_change_count_window": privilege_changes,
        "file_download_count_window": downloads,
        "api_error_count_window": api_errors,
        "bytes_sent_sum_window": bytes_received // 10,
        "bytes_received_sum_window": bytes_received,
        "is_authentication_event": 1,
        "is_file_access_event": float(downloads > 0),
        "is_privilege_change_event": float(privilege_changes > 0),
        "is_api_event": float(api_errors > 0),
        "is_failure_status": float(failures > 0 or api_errors > 0),
    }
