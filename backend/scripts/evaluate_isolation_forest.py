from __future__ import annotations

import argparse
import asyncio
import json

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ml.evaluation import evaluate_frames, persist_evaluation
from app.ml.synthetic import synthetic_feature_sets
from app.repositories.model_registry_repository import ModelRegistryRepository


async def run(*, rows: int, seed: int) -> dict:
    settings = get_settings()
    async with SessionLocal() as session:
        repository = ModelRegistryRepository(session)
        registry = await repository.get_active(settings.ml_model_name)
        if registry is None:
            raise RuntimeError(f"No active model named {settings.ml_model_name}")
        normal, abnormal = synthetic_feature_sets(rows=rows, seed=seed)
        metrics = evaluate_frames(
            registry.artifact_path,
            normal,
            abnormal,
            threshold=settings.ml_anomaly_alert_threshold,
        )
        await persist_evaluation(repository, registry, metrics)
        await session.commit()
    result = metrics.to_dict()
    print(json.dumps(result, indent=2))
    if not metrics.passed:
        raise RuntimeError("ML evaluation did not meet the Sprint 5 acceptance criteria")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate normal and abnormal synthetic telemetry.")
    parser.add_argument("--rows", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    asyncio.run(run(rows=args.rows, seed=args.seed))


if __name__ == "__main__":
    main()
