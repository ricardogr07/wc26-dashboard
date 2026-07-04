#!/usr/bin/env python3
"""Seed QF match documents into CosmosDB from R16 winners.

Reads completed R16 match documents, resolves winners, and upserts 4 QF
match documents using the official FIFA WC2026 QF schedule.  Teams not yet
determined get a TBD_R16_{id} placeholder.

Safe to re-run — uses upsert semantics.  Re-running after more R16 matches
complete will patch TBD placeholders with real team IDs.

Usage:
  # Dry run — prints what would be written, touches nothing:
  COSMOS_CONNECTION_STRING=<conn> python scripts/seed_qf.py

  # Write to production CosmosDB:
  COSMOS_CONNECTION_STRING=<conn> python scripts/seed_qf.py --apply
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

# Official FIFA WC2026 QF schedule (UTC kickoff times).
# (qf_id, scheduledAt, home_r16_id, away_r16_id, venue)
_QF_SCHEDULE: list[tuple[str, str, str, str, str]] = [
    ("qf_97", "2026-07-09T20:00:00Z", "r16_89", "r16_90", "Gillette Stadium, Foxborough"),
    ("qf_98", "2026-07-10T19:00:00Z", "r16_93", "r16_94", "SoFi Stadium, Inglewood"),
    ("qf_99", "2026-07-11T21:00:00Z", "r16_91", "r16_92", "Hard Rock Stadium, Miami Gardens"),
    ("qf_100", "2026-07-12T01:00:00Z", "r16_95", "r16_96", "Arrowhead Stadium, Kansas City"),
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
    print(f"{prefix}Loading R16 match results from CosmosDB...")

    r16_docs: dict[str, dict] = {}
    for doc in container.query_items(
        query="SELECT * FROM c WHERE c.type = 'match' AND c.round = 'r16'",
        enable_cross_partition_query=True,
    ):
        r16_docs[doc["id"]] = doc

    print(f"  Found {len(r16_docs)} R16 match doc(s).")

    def winner_of(r16_id: str) -> str:
        doc = r16_docs.get(r16_id)
        if doc and doc.get("winnerId"):
            return doc["winnerId"]
        return f"TBD_R16_{r16_id}"

    print(f"\n{prefix}QF documents to upsert:")

    now_iso = datetime.now(UTC).isoformat()
    upserted = 0

    for match_id, scheduled_at, home_r16, away_r16, venue in _QF_SCHEDULE:
        home_id = winner_of(home_r16)
        away_id = winner_of(away_r16)

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
            "round": "qf",
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
        for _, _, h, a, _ in _QF_SCHEDULE
        if winner_of(h).startswith("TBD") or winner_of(a).startswith("TBD")
    )
    if tbd:
        print(f"  {tbd} match(es) still have TBD slots -- re-run as R16 results come in.")


if __name__ == "__main__":
    main()
