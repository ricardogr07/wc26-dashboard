#!/usr/bin/env python3
"""Seed R16 match documents into CosmosDB from R32 winners.

Reads completed R32 match documents, resolves winners, and upserts 8 R16
match documents using the official FIFA WC2026 R16 schedule.  Teams not yet
determined (R32 not complete) get a TBD_R32_{id} placeholder.

Safe to re-run — uses upsert semantics.  Re-running after more R32 matches
complete will patch TBD placeholders with real team IDs.

Usage:
  # Dry run — prints what would be written, touches nothing:
  COSMOS_CONNECTION_STRING=<conn> python scripts/seed_r16.py

  # Write to production CosmosDB:
  COSMOS_CONNECTION_STRING=<conn> python scripts/seed_r16.py --apply
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

_EMULATOR_CONN = (
    "AccountEndpoint=https://localhost:8081/;"
    "AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b5hG9I/o6xK7xCy5h4HJf/qzl5s3v4sLQ==;"
)

# Official FIFA WC2026 R16 schedule (UTC kickoff times).
# (r16_id, scheduledAt, home_r32_id, away_r32_id, venue)
_R16_SCHEDULE: list[tuple[str, str, str, str, str]] = [
    ("r16_90", "2026-07-04T17:00:00Z", "r32_73", "r32_75", "NRG Stadium, Houston"),
    ("r16_89", "2026-07-04T21:00:00Z", "r32_74", "r32_77", "Lincoln Financial Field, Philadelphia"),
    ("r16_91", "2026-07-05T20:00:00Z", "r32_76", "r32_78", "MetLife Stadium, East Rutherford"),
    ("r16_92", "2026-07-06T00:00:00Z", "r32_79", "r32_80", "Estadio Azteca, Mexico City"),
    ("r16_93", "2026-07-06T19:00:00Z", "r32_83", "r32_84", "AT&T Stadium, Arlington"),
    ("r16_94", "2026-07-07T00:00:00Z", "r32_81", "r32_82", "Lumen Field, Seattle"),
    ("r16_95", "2026-07-07T16:00:00Z", "r32_86", "r32_88", "Mercedes-Benz Stadium, Atlanta"),
    ("r16_96", "2026-07-07T20:00:00Z", "r32_85", "r32_87", "BC Place, Vancouver"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    args = parser.parse_args()

    conn = os.environ.get("COSMOS_CONNECTION_STRING", _EMULATOR_CONN)
    db_name = os.environ.get("COSMOS_DATABASE_NAME", "wc26db")
    ctr_name = os.environ.get("COSMOS_CONTAINER_NAME", "items")

    verify_ssl = "localhost" not in conn and "127.0.0.1" not in conn
    client = CosmosClient.from_connection_string(conn, connection_verify=verify_ssl)
    container = client.get_database_client(db_name).get_container_client(ctr_name)

    try:
        container.read()
    except Exception as exc:
        print(f"ERROR: cannot reach {db_name}/{ctr_name}: {exc}", file=sys.stderr)
        sys.exit(1)

    prefix = "[DRY RUN] " if not args.apply else ""
    print(f"{prefix}Loading R32 match results from CosmosDB...")

    r32_docs: dict[str, dict] = {}
    for doc in container.query_items(
        query="SELECT * FROM c WHERE c.type = 'match' AND c.round = 'r32'",
        enable_cross_partition_query=True,
    ):
        r32_docs[doc["id"]] = doc

    print(f"  Found {len(r32_docs)} R32 match doc(s).")

    def winner_of(r32_id: str) -> str:
        doc = r32_docs.get(r32_id)
        if doc and doc.get("winnerId"):
            return doc["winnerId"]
        return f"TBD_R32_{r32_id}"

    print(f"\n{prefix}R16 documents to upsert:")

    now_iso = datetime.now(UTC).isoformat()
    upserted = 0

    for match_id, scheduled_at, home_r32, away_r32, venue in _R16_SCHEDULE:
        home_id = winner_of(home_r32)
        away_id = winner_of(away_r32)

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
            "round": "r16",
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

    suffix = "" if args.apply else " (dry run — use --apply to write)"
    print(f"\nDone{suffix}: {upserted} document(s) written.")
    tbd = sum(
        1
        for _, _, h, a, _ in _R16_SCHEDULE
        if winner_of(h).startswith("TBD") or winner_of(a).startswith("TBD")
    )
    if tbd:
        print(f"  {tbd} match(es) still have TBD slots — re-run as R32 results come in.")


if __name__ == "__main__":
    main()
