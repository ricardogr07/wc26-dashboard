#!/usr/bin/env python3
"""DB status diagnostic — shows team statuses, match results by round, and TBD slots.

Usage:
  python scripts/check_db.py
  python scripts/check_db.py --round r16
  python scripts/check_db.py --points
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

for line in (Path(__file__).parents[1] / ".env.local").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from azure.cosmos import CosmosClient  # noqa: E402

ROUND_ORDER = ["group", "r32", "r16", "qf", "sf", "final"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", help="Filter to a specific round (e.g. r16, qf)")
    parser.add_argument("--points", action="store_true", help="Show participant points summary")
    args = parser.parse_args()

    conn = os.environ.get("COSMOS_CONNECTION_STRING", "")
    if not conn:
        print("ERROR: COSMOS_CONNECTION_STRING not set", file=sys.stderr)
        sys.exit(1)

    db_name = os.environ.get("COSMOS_DATABASE_NAME", "wc26db")
    ctr_name = os.environ.get("COSMOS_CONTAINER_NAME", "items")
    verify_ssl = "localhost" not in conn and "127.0.0.1" not in conn

    client = CosmosClient.from_connection_string(conn, connection_verify=verify_ssl)
    container = client.get_database_client(db_name).get_container_client(ctr_name)

    # --- Teams ---
    teams = list(
        container.query_items(
            "SELECT c.id, c.name, c.status FROM c WHERE c.type = 'team'",
            enable_cross_partition_query=True,
        )
    )
    by_status: dict[str, list[str]] = defaultdict(list)
    for t in teams:
        by_status[t.get("status", "unknown")].append(t["id"])

    print("=== Team Status ===")
    for status in ["active", "eliminated", "champion", "unknown"]:
        ids = sorted(by_status.get(status, []))
        if ids:
            print(f"  {status} ({len(ids):2d}): {', '.join(ids)}")

    # --- Matches ---
    matches = list(
        container.query_items(
            "SELECT * FROM c WHERE c.type = 'match'",
            enable_cross_partition_query=True,
        )
    )

    by_round: dict[str, list[dict]] = defaultdict(list)
    for m in matches:
        by_round[m.get("round", "?")].append(m)

    rounds_to_show = [args.round] if args.round else ROUND_ORDER
    print("\n=== Matches by Round ===")
    for rnd in rounds_to_show:
        docs = by_round.get(rnd, [])
        if not docs and args.round:
            print(f"  {rnd}: no documents found")
            continue
        if not docs:
            continue
        completed = sum(1 for m in docs if m.get("status") == "completed")
        scheduled = sum(1 for m in docs if m.get("status") == "scheduled")
        live = sum(1 for m in docs if m.get("status") == "live")
        parts = [f"{completed} completed"]
        if live:
            parts.append(f"{live} live")
        if scheduled:
            parts.append(f"{scheduled} scheduled")
        print(f"  {rnd:6s} ({len(docs):2d}): {', '.join(parts)}")

    # --- TBD Slots ---
    tbd_matches = [
        m
        for m in matches
        if (
            m.get("homeTeamId", "").startswith("TBD_") or m.get("awayTeamId", "").startswith("TBD_")
        )
        and m.get("status") != "completed"
    ]
    if tbd_matches and (not args.round or any(m.get("round") == args.round for m in tbd_matches)):
        print("\n=== TBD Slots ===")
        for m in sorted(tbd_matches, key=lambda x: x.get("scheduledAt", "")):
            rnd = m.get("round", "?")
            if args.round and rnd != args.round:
                continue
            h = m.get("homeTeamId", "?")
            a = m.get("awayTeamId", "?")
            date = (m.get("scheduledAt") or "")[:10]
            print(f"  {m['id']:10s} ({rnd}, {date}): {h} vs {a}")

    # --- Points (optional) ---
    if args.points:
        # Re-implement basic scoring inline to avoid import path issues
        round_points = {"r32": 2, "r16": 3, "qf": 5, "sf": 8, "final": 13}
        print("\n=== Points (from completed knockout matches) ===")
        points: dict[str, int] = defaultdict(int)
        for m in matches:
            rnd = m.get("round", "group")
            winner = m.get("winnerId")
            if m.get("status") == "completed" and winner and rnd in round_points:
                points[winner] += round_points[rnd]
        for tid, pts in sorted(points.items(), key=lambda x: -x[1])[:20]:
            name = next((t.get("name", tid) for t in teams if t["id"] == tid), tid)
            print(f"  {tid:4s} ({name}): {pts} pts")


if __name__ == "__main__":
    main()
