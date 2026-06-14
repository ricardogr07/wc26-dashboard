#!/usr/bin/env python3
"""Upsert all seed documents (participants, teams, fixtures) into Cosmos DB.

Prerequisites:
  Emulator:  docker compose up --wait
             python scripts/setup_emulator.py   (run once to create db/container)
  Real Azure: set COSMOS_CONNECTION_STRING env var

Usage:
  python scripts/seed_cosmos.py            # safe: skip documents that already exist
  python scripts/seed_cosmos.py --force    # overwrite existing documents
  COSMOS_CONNECTION_STRING=<real> python scripts/seed_cosmos.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceExistsError

SEED_DIR = Path(__file__).parent.parent / "shared" / "seed"

_EMULATOR_CONN = (
    "AccountEndpoint=https://localhost:8081/;"
    "AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b5hG9I/o6xK7xCy5h4HJf/qzl5s3v4sLQ==;"
)

_SEED_FILES = ["participants.json", "teams.json", "fixtures.json"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing documents (upsert). Default skips existing docs to avoid clobbering live data.",
    )
    args = parser.parse_args()

    conn = os.environ.get("COSMOS_CONNECTION_STRING", _EMULATOR_CONN)
    db_name = os.environ.get("COSMOS_DATABASE_NAME", "wc26db")
    ctr_name = os.environ.get("COSMOS_CONTAINER_NAME", "items")

    verify_ssl = "localhost" not in conn and "127.0.0.1" not in conn
    client = CosmosClient.from_connection_string(conn, connection_verify=verify_ssl)
    container = client.get_database_client(db_name).get_container_client(ctr_name)

    # Quick connectivity check
    try:
        container.read()
    except Exception as exc:
        print(f"ERROR: cannot reach {db_name}/{ctr_name}: {exc}", file=sys.stderr)
        print("Tip: run `docker compose up --wait` then `python scripts/setup_emulator.py`")
        sys.exit(1)

    total_written = 0
    total_skipped = 0
    for filename in _SEED_FILES:
        path = SEED_DIR / filename
        if not path.exists():
            print(f"  SKIP {filename} (not found)")
            continue
        docs = json.loads(path.read_text(encoding="utf-8"))
        written = skipped = 0
        for doc in docs:
            if args.force:
                container.upsert_item(doc)
                written += 1
            else:
                try:
                    container.create_item(doc)
                    written += 1
                except CosmosResourceExistsError:
                    skipped += 1
        print(f"  OK   {filename}: {written} written, {skipped} skipped (already exist)")
        total_written += written
        total_skipped += skipped

    print(f"\nDone — {total_written} written, {total_skipped} skipped into {db_name}/{ctr_name}")
    if total_skipped and not args.force:
        print("Tip: use --force to overwrite existing documents.")


if __name__ == "__main__":
    main()
