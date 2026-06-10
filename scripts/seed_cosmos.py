#!/usr/bin/env python3
"""Upsert all seed documents (participants, teams, fixtures) into Cosmos DB.

Prerequisites:
  Emulator:  docker compose up --wait
             python scripts/setup_emulator.py   (run once to create db/container)
  Real Azure: set COSMOS_CONNECTION_STRING env var

Usage:
  python scripts/seed_cosmos.py
  COSMOS_CONNECTION_STRING=<real> python scripts/seed_cosmos.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from azure.cosmos import CosmosClient

SEED_DIR = Path(__file__).parent.parent / "shared" / "seed"

_EMULATOR_CONN = (
    "AccountEndpoint=https://localhost:8081/;"
    "AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b5hG9I/o6xK7xCy5h4HJf/qzl5s3v4sLQ==;"
)

_SEED_FILES = ["participants.json", "teams.json", "fixtures.json"]


def main() -> None:
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

    total = 0
    for filename in _SEED_FILES:
        path = SEED_DIR / filename
        if not path.exists():
            print(f"  SKIP {filename} (not found)")
            continue
        docs = json.loads(path.read_text(encoding="utf-8"))
        for doc in docs:
            container.upsert_item(doc)
        print(f"  OK   {filename}: {len(docs)} documents upserted")
        total += len(docs)

    print(f"\nDone — {total} total documents seeded into {db_name}/{ctr_name}")


if __name__ == "__main__":
    main()
