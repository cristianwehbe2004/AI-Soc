from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import pandas as pd

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ml.training import train_model
from app.repositories.model_registry_repository import ModelRegistryRepository


async def run(dataset: Path) -> str:
    settings = get_settings()
    frame = pd.read_csv(dataset)
    async with SessionLocal() as session:
        registry = await train_model(
            frame,
            repository=ModelRegistryRepository(session),
            settings=settings,
        )
        await session.commit()
    print(f"Activated {registry.model_version}: {registry.artifact_path}")
    return registry.model_version


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and activate the Sprint 5 Isolation Forest model.")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    asyncio.run(run(args.dataset))


if __name__ == "__main__":
    main()
