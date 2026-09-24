from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.main import app


def render_schema() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the FastAPI OpenAPI schema")
    parser.add_argument("output", help="Output path, or '-' for stdout")
    parser.add_argument("--check", action="store_true", help="Fail if output is stale")
    args = parser.parse_args()
    rendered = render_schema()
    if args.output == "-":
        print(rendered, end="")
        return

    output = Path(args.output)
    if args.check:
        if not output.exists() or output.read_text() != rendered:
            raise SystemExit(f"OpenAPI snapshot is stale: {output}")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered)


if __name__ == "__main__":
    main()
