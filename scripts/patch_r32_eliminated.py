#!/usr/bin/env python3
"""One-shot backfill: mark R32 losers as 'eliminated'.

Reads all completed R32 match documents, finds the loser of each (the team
that is NOT winnerId), and patches their status to 'eliminated'.

Safe to re-run — skips teams already marked eliminated.

Usage:
  COSMOS_CONNECTION_STRING=<conn> python scripts/patch_r32_eliminated.py
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

for line in (Path(__file__).parents[1] / ".env.local").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from azure.cosmos import CosmosClient  # noqa: E402

conn = os.environ["COSMOS_CONNECTION_STRING"]
container = (
    CosmosClient.from_connection_string(conn)
    .get_database_client(os.environ.get("COSMOS_DATABASE_NAME", "wc26db"))
    .get_container_client(os.environ.get("COSMOS_CONTAINER_NAME", "items"))
)
now_iso = datetime.now(UTC).isoformat()

r32_matches = list(
    container.query_items(
        query=(
            "SELECT * FROM c WHERE c.type = 'match' AND c.round = 'r32'"
            " AND c.status = 'completed' AND c.winnerId != null"
        ),
        enable_cross_partition_query=True,
    )
)

print(f"Found {len(r32_matches)} completed R32 match(es) with a winner.")
eliminated = 0

for m in r32_matches:
    winner_id = m["winnerId"]
    home_id = m.get("homeTeamId", "")
    away_id = m.get("awayTeamId", "")
    loser_id = away_id if winner_id == home_id else home_id

    if not loser_id or loser_id.startswith("TBD"):
        print(f"  {m['id']}: loser ID {loser_id!r} is unresolved, skipping")
        continue

    try:
        team = container.read_item(item=loser_id, partition_key="team")
    except Exception:
        print(f"  {m['id']}: team doc {loser_id} not found, skipping")
        continue

    if team.get("status") == "eliminated":
        print(f"  {m['id']}: {loser_id} already eliminated, skip")
        continue

    container.patch_item(
        item=loser_id,
        partition_key="team",
        patch_operations=[
            {"op": "set", "path": "/status", "value": "eliminated"},
            {"op": "set", "path": "/lastUpdated", "value": now_iso},
        ],
    )
    container.create_item(
        {
            "id": f"audit_{uuid.uuid4().hex}",
            "type": "audit",
            "action": "team_eliminated",
            "teamId": loser_id,
            "matchId": m["id"],
            "appliedAt": now_iso,
        }
    )
    print(f"  {m['id']}: {winner_id} won -> {loser_id} eliminated")
    eliminated += 1

print(f"\nDone: {eliminated} team(s) marked eliminated.")
