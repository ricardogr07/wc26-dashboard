#!/usr/bin/env python3
"""Seed Final match document into CosmosDB from SF winners.

Safe to re-run — uses upsert semantics.

Usage:
  python scripts/seed_final.py           # dry run
  python scripts/seed_final.py --apply   # write to CosmosDB
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

for line in (Path(__file__).parents[1] / ".env.local").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from azure.cosmos import CosmosClient  # noqa: E402

# Official FIFA WC2026 Final schedule (UTC kickoff time).
# (final_id, scheduledAt, home_sf_id, away_sf_id, venue)
_FINAL_SCHEDULE: list[tuple[str, str, str, str, str]] = [
    ("final_104", "2026-07-19T19:00:00Z", "sf_101", "sf_102", "MetLife Stadium, East Rutherford"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
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

    prefix = "[DRY RUN] " if not args.apply else ""
    sf_docs: dict[str, dict] = {}
    for doc in container.query_items(
        query="SELECT * FROM c WHERE c.type = 'match' AND c.round = 'sf'",
        enable_cross_partition_query=True,
    ):
        sf_docs[doc["id"]] = doc

    print(f"{prefix}Found {len(sf_docs)} SF match doc(s).")

    def winner_of(sf_id: str) -> str:
        doc = sf_docs.get(sf_id)
        if doc and doc.get("winnerId"):
            return doc["winnerId"]
        return f"TBD_SF_{sf_id}"

    print(f"\n{prefix}Final document to upsert:")
    now_iso = datetime.now(UTC).isoformat()
    upserted = 0

    for match_id, scheduled_at, home_sf, away_sf, venue in _FINAL_SCHEDULE:
        home_id = winner_of(home_sf)
        away_id = winner_of(away_sf)

        existing_home = existing_away = existing_status = None
        try:
            existing = container.read_item(item=match_id, partition_key="match")
            existing_home = existing.get("homeTeamId")
            existing_away = existing.get("awayTeamId")
            existing_status = existing.get("status")
        except Exception:
            pass

        change = (existing_home != home_id) or (existing_away != away_id)
        marker = "NEW  " if existing_home is None else ("UPD  " if change else "SAME ")
        print(
            f"  {marker}{match_id}  {home_id:20s} vs {away_id}"
            + (f"  [was: {existing_home} vs {existing_away}]" if change and existing_home else "")
        )

        if not args.apply:
            continue

        doc: dict = {
            "id": match_id,
            "type": "match",
            "round": "final",
            "group": None,
            "homeTeamId": home_id,
            "awayTeamId": away_id,
            "scheduledAt": scheduled_at,
            "venue": venue,
            "homeScore": None,
            "awayScore": None,
            "winnerId": None,
            "status": existing_status or "scheduled",
            "source": "bracket",
            "lastUpdated": now_iso,
        }
        container.upsert_item(doc)
        upserted += 1

    suffix = "" if args.apply else " (dry run -- use --apply to write)"
    print(f"\nDone{suffix}: {upserted} document(s) written.")
    tbd = sum(
        1
        for _, _, h, a, _ in _FINAL_SCHEDULE
        if winner_of(h).startswith("TBD") or winner_of(a).startswith("TBD")
    )
    if tbd:
        print(f"  {tbd} match(es) still have TBD slots -- re-run as SF results come in.")


if __name__ == "__main__":
    main()
