from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from app.db.session import SessionLocal, engine
from app.services.bootstrap_service import create_first_admin


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the first AI-SOC administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    return parser.parse_args()


async def create_admin(email: str, full_name: str, password: str) -> bool:
    async with SessionLocal() as session:
        created = await create_first_admin(
            session,
            email=email,
            full_name=full_name,
            password=password,
        )
    message = "Administrator created" if created else "Administrator already exists"
    print(f"{message}: {email.strip().casefold()}")
    return created


async def main() -> None:
    args = parse_args()
    password = getpass.getpass("Password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise RuntimeError("Passwords do not match")
    if len(password) < 12 or len(password) > 128:
        raise RuntimeError("Password must contain between 12 and 128 characters")
    try:
        await create_admin(args.email, args.full_name, password)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
