"""Explicit, bounded, read-only S3 input for local incident-classifier training."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.ml.incident_classifier import LabeledCase, parse_cases

DEFAULT_MAX_BYTES = 5 * 1024 * 1024
MAX_ALLOWED_BYTES = 20 * 1024 * 1024
BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")


@dataclass(frozen=True)
class S3DatasetPlan:
    bucket: str
    key: str
    account_id: str
    max_bytes: int


def plan_s3_dataset(
    uri: str, *, account_id: str, allowed_bucket: str,
    allowed_prefix: str, max_bytes: int = DEFAULT_MAX_BYTES,
) -> S3DatasetPlan:
    """Validate an exact object and scope without creating an AWS client."""
    parsed = urlsplit(uri)
    if parsed.scheme != "s3" or parsed.query or parsed.fragment or not parsed.netloc:
        raise ValueError("Expected an exact s3://bucket/key.jsonl URI without query or fragment")
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    if not BUCKET_PATTERN.fullmatch(bucket) or ".." in bucket or bucket != allowed_bucket:
        raise ValueError("S3 bucket is invalid or outside the explicit allowlist")
    if not re.fullmatch(r"\d{12}", account_id):
        raise ValueError("An exact 12-digit AWS account ID is required")
    prefix = allowed_prefix.strip("/")
    if not prefix or any(part in {"", ".", ".."} for part in prefix.split("/")):
        raise ValueError("A non-empty, safe S3 prefix is required")
    if not key.startswith(prefix + "/") or not key.endswith(".jsonl"):
        raise ValueError("Dataset must be a JSONL object below the allowlisted prefix")
    if any(part in {"", ".", ".."} for part in key.split("/")) or "%" in key:
        raise ValueError("Dataset key must not contain ambiguous path segments or encoding")
    if not 1 <= max_bytes <= MAX_ALLOWED_BYTES:
        raise ValueError(f"AWS dataset cap must be between 1 and {MAX_ALLOWED_BYTES} bytes")
    return S3DatasetPlan(bucket=bucket, key=key, account_id=account_id, max_bytes=max_bytes)


def load_s3_cases(plan: S3DatasetPlan, *, aws_session=None) -> tuple[list[LabeledCase], str]:
    """Fetch one object after opt-in; never writes data or creates cloud resources."""
    if aws_session is None:
        import boto3

        aws_session = boto3.Session()
    identity = aws_session.client("sts").get_caller_identity()
    if identity.get("Account") != plan.account_id:
        raise ValueError("AWS credentials do not target the allowlisted account")
    client = aws_session.client("s3")
    head = client.head_object(
        Bucket=plan.bucket, Key=plan.key, ExpectedBucketOwner=plan.account_id,
    )
    size = head.get("ContentLength")
    if not isinstance(size, int) or size < 1 or size > plan.max_bytes:
        raise ValueError("S3 dataset is empty, too large, or has unknown size")
    if head.get("StorageClass", "STANDARD") != "STANDARD":
        raise ValueError("Only S3 Standard objects are accepted to avoid retrieval surprises")
    etag = head.get("ETag")
    if not isinstance(etag, str) or not etag:
        raise ValueError("S3 dataset must have an ETag to guard against changes during download")
    options = {
        "Bucket": plan.bucket,
        "Key": plan.key,
        "ExpectedBucketOwner": plan.account_id,
        "IfMatch": etag,
    }
    response = client.get_object(**options)
    body = response["Body"]
    try:
        data = body.read(plan.max_bytes + 1)
    finally:
        body.close()
    if len(data) != size:
        raise ValueError("S3 dataset changed or exceeded the configured size cap")
    digest = hashlib.sha256(data).hexdigest()
    return parse_cases(data.decode("utf-8")), digest
