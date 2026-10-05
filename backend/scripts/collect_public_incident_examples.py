"""Collect bounded OTRF scenario metadata for analyst review, not model training.

Only metadata YAML is read. Raw telemetry archives, adversary transcripts and
simulation commands are deliberately never downloaded or persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

REPOSITORY = "OTRF/Security-Datasets"
COMMIT = "d9d40ef123d2c87d5d3df28c96bcab4f0faccc87"
TREE_URL = f"https://api.github.com/repos/{REPOSITORY}/git/trees/{COMMIT}?recursive=1"
RAW_BASE = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/"
MAX_FILE_BYTES = 256_000
MAX_SCENARIOS = 200
METADATA_PATH = re.compile(r"^datasets/(atomic|compound)/_metadata/[A-Za-z0-9_.-]+\.yaml$")
SENSITIVE = re.compile(r"(?i)(AKIA|ASIA)[A-Z0-9]{16}|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|\b(?:\d{1,3}\.){3}\d{1,3}\b")


def fetch(url: str, *, max_bytes: int = MAX_FILE_BYTES) -> bytes:
    if not (url.startswith("https://api.github.com/repos/OTRF/Security-Datasets/") or
            url.startswith(RAW_BASE)):
        raise ValueError("URL is outside the pinned source")
    request = Request(url, headers={"User-Agent": "ai-soc-public-scenario-research/1.0", "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"Source exceeds {max_bytes} bytes: {url}")
    return data


def clean(value: object, limit: int) -> str:
    text = " ".join(str(value or "").split())[:limit]
    return SENSITIVE.sub("[redacted]", text)


def project_metadata(path: str, body: bytes) -> dict:
    if not METADATA_PATH.fullmatch(path):
        raise ValueError("Only scenario metadata YAML is permitted")
    source = yaml.safe_load(body.decode("utf-8-sig"))
    if not isinstance(source, dict) or not source.get("id") or not source.get("title"):
        raise ValueError("Scenario has no ID or title")
    mappings = source.get("attack_mappings") or []
    if not isinstance(mappings, list):
        mappings = []
    techniques = sorted({str(item["technique"]) for item in mappings if isinstance(item, dict) and item.get("technique")})
    tags = source.get("tags") or []
    platforms = source.get("platform") or []
    return {
        "scenario_id": clean(source["id"], 80),
        "title": clean(source["title"], 200),
        "summary": clean(source.get("description"), 400),
        "tags": [clean(item, 100) for item in tags[:20]] if isinstance(tags, list) else [],
        "platforms": [clean(item, 60) for item in platforms[:10]] if isinstance(platforms, list) else [],
        "attack_techniques": techniques,
        "source_url": f"https://github.com/{REPOSITORY}/blob/{COMMIT}/{path}",
        "source_commit": COMMIT,
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "kind": "attack_simulation_metadata",
        "review_status": "unreviewed",
        "train_ready": False,
    }


def collect(limit: int, delay_seconds: float) -> list[dict]:
    tree = json.loads(fetch(TREE_URL, max_bytes=2_000_000))
    if tree.get("truncated"):
        raise ValueError("Source tree is truncated")
    paths = sorted(item["path"] for item in tree["tree"] if item.get("type") == "blob" and METADATA_PATH.fullmatch(item["path"]))
    if not paths:
        raise ValueError("No metadata files found at pinned commit")
    records = []
    seen_ids = set()
    for path in paths[:limit]:
        record = project_metadata(path, fetch(RAW_BASE + path))
        if record["scenario_id"] in seen_ids:
            raise ValueError(f"Duplicate scenario ID: {record['scenario_id']}")
        seen_ids.add(record["scenario_id"])
        records.append(record)
        if delay_seconds:
            time.sleep(delay_seconds)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/public_incident_examples.jsonl"))
    parser.add_argument("--limit", type=int, default=MAX_SCENARIOS)
    parser.add_argument("--delay-seconds", type=float, default=0.15)
    args = parser.parse_args()
    if not 1 <= args.limit <= MAX_SCENARIOS or not 0 <= args.delay_seconds <= 10:
        parser.error("limit must be 1..200 and delay 0..10 seconds")
    records = collect(args.limit, args.delay_seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")
    print(f"Collected {len(records)} unreviewed scenarios into {args.output}; not train-ready")


if __name__ == "__main__":
    main()
