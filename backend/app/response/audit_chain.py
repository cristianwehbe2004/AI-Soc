from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    """Produces deterministic, canonical JSON encoding for cryptographic hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def compute_entry_hash(prev_hash: str, entry_payload: dict[str, Any]) -> str:
    """Computes SHA-256(prev_hash + canonical_json(entry_payload))."""
    serialized = canonical_json(entry_payload)
    hasher = hashlib.sha256()
    hasher.update(prev_hash.encode("utf-8"))
    hasher.update(serialized.encode("utf-8"))
    return hasher.hexdigest()


def verify_chain(records: list[dict[str, Any]], initial_prev_hash: str = "0" * 64) -> tuple[bool, str | None]:
    """
    Verifies that a sequence of audit records forms an unbroken cryptographic chain.
    Returns (True, None) if completely valid, or (False, failure_reason) on any discrepancy.
    """
    current_prev_hash = initial_prev_hash

    for index, record in enumerate(records):
        record_prev_hash = record.get("prev_hash")
        record_hash = record.get("record_hash")
        record_id = record.get("id", f"index_{index}")

        if not record_prev_hash or not record_hash:
            return False, f"Missing hash pointers at record {record_id}"

        if record_prev_hash != current_prev_hash:
            return False, (
                f"Broken chain linkage at record {record_id}: "
                f"expected prev_hash {current_prev_hash}, found {record_prev_hash}"
            )

        payload = {
            k: v for k, v in record.items()
            if k not in {"record_hash", "id"}
        }

        expected_hash = compute_entry_hash(current_prev_hash, payload)
        if record_hash != expected_hash:
            return False, (
                f"Hash mismatch at record {record_id}: record payload was tampered with or recalculated incorrectly"
            )

        current_prev_hash = record_hash

    return True, None
