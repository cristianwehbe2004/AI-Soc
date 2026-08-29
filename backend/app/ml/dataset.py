from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from app.ml.features import FEATURE_COLUMNS, build_feature_vector
from app.models.event import Event
from app.repositories.event_repository import EventRepository


def build_dataset(events: list[Event], *, window_seconds: int) -> pd.DataFrame:
    ordered = sorted(events, key=lambda item: (item.timestamp, item.created_at))
    rows: list[dict[str, float]] = []
    left = 0
    for index, event in enumerate(ordered):
        cutoff = event.timestamp - timedelta(seconds=window_seconds)
        while left < index and ordered[left].timestamp < cutoff:
            left += 1
        rows.append(build_feature_vector(event, ordered[left : index + 1]))
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS).fillna(0.0)


async def generate_dataset(
    repository: EventRepository,
    *,
    end_time: datetime,
    lookback_days: int,
    window_seconds: int,
) -> pd.DataFrame:
    events = await repository.list_between(
        start_time=end_time - timedelta(days=lookback_days),
        end_time=end_time,
    )
    return build_dataset(events, window_seconds=window_seconds)


def write_dataset(frame: pd.DataFrame, output_path: Path, *, metadata: dict | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    metadata_path = output_path.with_suffix(".metadata.json")
    metadata_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).isoformat(),
                "row_count": len(frame),
                "feature_columns": FEATURE_COLUMNS,
                **(metadata or {}),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return metadata_path
