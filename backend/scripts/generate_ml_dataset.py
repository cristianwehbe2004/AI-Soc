from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ml.dataset import generate_dataset, write_dataset
from app.repositories.event_repository import EventRepository


async def run(output: Path) -> int:
    settings = get_settings()
    async with SessionLocal() as session:
        frame = await generate_dataset(
            EventRepository(session),
            end_time=datetime.now(UTC),
            lookback_days=settings.ml_training_lookback_days,
            window_seconds=settings.ml_aggregation_window_seconds,
        )
    write_dataset(
        frame,
        output,
        metadata={
            "feature_version": settings.ml_feature_version,
            "lookback_days": settings.ml_training_lookback_days,
            "window_seconds": settings.ml_aggregation_window_seconds,
        },
    )
    print(f"Wrote {len(frame)} feature rows to {output}")
    return len(frame)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an ML training dataset from stored events.")
    parser.add_argument("--output", type=Path, default=Path("artifacts/datasets/events_v1.csv"))
    args = parser.parse_args()
    asyncio.run(run(args.output))


if __name__ == "__main__":
    main()
