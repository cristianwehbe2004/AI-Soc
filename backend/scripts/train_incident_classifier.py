from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.ml.aws_dataset import load_s3_cases, plan_s3_dataset
from app.ml.incident_classifier import LabeledCase, load_cases, train_incident_classifier
from app.ml.training_examples import load_training_cases
from app.repositories.model_registry_repository import ModelRegistryRepository


async def run(
    path: Path | None, activate: bool, *, from_db: bool = False,
    lab_shadow: bool = False, supplied_cases: list[LabeledCase] | None = None,
    dataset_provenance: dict | None = None,
) -> None:
    from app.core.config import get_settings
    from app.db.session import SessionLocal

    if lab_shadow and activate:
        raise ValueError("Synthetic lab cases cannot be activated")
    async with SessionLocal() as session:
        if supplied_cases is not None:
            cases = supplied_cases
        elif from_db:
            cases = await load_training_cases(session, lab_shadow=lab_shadow)
        elif path is not None:
            cases = load_cases(path)
        else:
            raise ValueError("A training dataset is required")
        registry = await train_incident_classifier(
            cases, ModelRegistryRepository(session), get_settings(),
            activate=activate, dataset_provenance=dataset_provenance,
        )
        await session.commit()
        print(f"{registry.status}: {registry.model_version}; evaluation={registry.evaluation_metrics}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train incident classifier from reviewed JSONL cases")
    parser.add_argument("dataset", type=Path, nargs="?")
    parser.add_argument("--from-db", action="store_true", help="Load approved reviewed cases from training_incidents")
    parser.add_argument("--lab-shadow", action="store_true", help="With --from-db, train on synthetic cases in shadow mode only")
    parser.add_argument("--activate", action="store_true", help="Activate only when test gates pass")
    parser.add_argument("--s3-uri", help="Exact s3://bucket/prefix/dataset.jsonl training input")
    parser.add_argument("--aws-account-id", help="Exact 12-digit account ID for S3 read")
    parser.add_argument("--aws-bucket", help="Exact allowlisted S3 bucket")
    parser.add_argument("--aws-prefix", help="Non-empty allowlisted S3 key prefix")
    parser.add_argument("--aws-max-bytes", type=int, default=5 * 1024 * 1024)
    parser.add_argument("--execute-aws-read", action="store_true", help="Opt in to STS, S3 HEAD, and S3 GET requests")
    args = parser.parse_args()
    if not args.s3_uri and any([args.aws_account_id, args.aws_bucket, args.aws_prefix, args.execute_aws_read]):
        parser.error("AWS read options require --s3-uri")
    if sum([args.dataset is not None, args.from_db, args.s3_uri is not None]) != 1:
        parser.error("Provide exactly one dataset path, --from-db, or --s3-uri")
    if args.lab_shadow and not args.from_db:
        parser.error("--lab-shadow requires --from-db")
    if args.s3_uri:
        if not args.aws_account_id or not args.aws_bucket or not args.aws_prefix:
            parser.error("S3 input requires --aws-account-id, --aws-bucket, and --aws-prefix")
        try:
            plan = plan_s3_dataset(
                args.s3_uri, account_id=args.aws_account_id,
                allowed_bucket=args.aws_bucket, allowed_prefix=args.aws_prefix,
                max_bytes=args.aws_max_bytes,
            )
        except ValueError as exc:
            parser.error(str(exc))
        if not args.execute_aws_read:
            print(
                f"DRY RUN: read s3://{plan.bucket}/{plan.key} from account {plan.account_id}; "
                f"cap={plan.max_bytes} bytes. No AWS calls or training performed. "
                "Add --execute-aws-read to proceed."
            )
        else:
            cases, digest = load_s3_cases(plan)
            print(f"Loaded {len(cases)} reviewed-case candidates; SHA-256={digest}")
            asyncio.run(run(None, args.activate, supplied_cases=cases, dataset_provenance={
                "kind": "s3", "uri": args.s3_uri,
                "account_id": plan.account_id, "sha256": digest,
            }))
    else:
        asyncio.run(run(args.dataset, args.activate, from_db=args.from_db, lab_shadow=args.lab_shadow))
