from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.db.session import SessionLocal
from app.ml.training_examples import seed_training_incidents


async def run(public_path: Path, per_class: int) -> None:
    async with SessionLocal() as session:
        inserted = await seed_training_incidents(session, public_path, per_class=per_class)
        await session.commit()
    print(f"Training-only examples inserted: {inserted}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed isolated synthetic lab cases and unreviewed public references")
    parser.add_argument("--public-path", type=Path, default=Path("data/public_incident_examples.jsonl"))
    parser.add_argument("--per-class", type=int, default=30)
    args = parser.parse_args()
    asyncio.run(run(args.public_path, args.per_class))
