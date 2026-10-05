from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ml.incident_classifier import load_cases, train_incident_classifier
from app.ml.training_examples import load_training_cases
from app.repositories.model_registry_repository import ModelRegistryRepository


async def run(path: Path | None, activate: bool, *, from_db: bool = False, lab_shadow: bool = False) -> None:
    if lab_shadow and activate:
        raise ValueError("Synthetic lab cases cannot be activated")
    async with SessionLocal() as session:
        cases = await load_training_cases(session, lab_shadow=lab_shadow) if from_db else load_cases(path)
        registry = await train_incident_classifier(cases, ModelRegistryRepository(session), get_settings(), activate=activate)
        await session.commit()
        print(f"{registry.status}: {registry.model_version}; evaluation={registry.evaluation_metrics}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train incident classifier from reviewed JSONL cases")
    parser.add_argument("dataset", type=Path, nargs="?")
    parser.add_argument("--from-db", action="store_true", help="Load approved reviewed cases from training_incidents")
    parser.add_argument("--lab-shadow", action="store_true", help="With --from-db, train on synthetic cases in shadow mode only")
    parser.add_argument("--activate", action="store_true", help="Activate only when test gates pass")
    args = parser.parse_args()
    if (args.dataset is None) == (not args.from_db):
        parser.error("Provide either a dataset path or --from-db")
    if args.lab_shadow and not args.from_db:
        parser.error("--lab-shadow requires --from-db")
    asyncio.run(run(args.dataset, args.activate, from_db=args.from_db, lab_shadow=args.lab_shadow))
