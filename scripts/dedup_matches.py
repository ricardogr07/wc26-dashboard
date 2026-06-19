#!/usr/bin/env python3
"""One-time migration: dedup match documents and fix stale "live" statuses in CosmosDB.

Two problems this fixes:
  1. Duplicate match documents — a wiki_XXX seeded doc and a tsdb_XXX sync doc exist
     for the same (homeTeamId, awayTeamId) pair. Keep the one with the best status
     (completed > live > scheduled, then newer lastUpdated) and delete the other.
  2. Stale "live" matches — matches with final scores that are still marked "live"
     because TheSportsDB kept returning an in-progress status code after the final
     whistle. Any match with scores set whose scheduledAt is >3 hours in the past
     is promoted to "completed".

Usage:
  # Dry run (default) — prints what would change, touches nothing:
  python scripts/dedup_matches.py

  # Apply changes to prod:
  COSMOS_CONNECTION_STRING=<conn> python scripts/dedup_matches.py --apply

  # Local emulator:
  python scripts/dedup_matches.py --apply
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from azure.cosmos import CosmosClient

_EMULATOR_CONN = (
    "AccountEndpoint=https://localhost:8081/;"
    "AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b5hG9I/o6xK7xCy5h4HJf/qzl5s3v4sLQ==;"
)

_STATUS_RANK = {"completed": 0, "live": 1, "scheduled": 2}


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _best_doc(docs: list[dict]) -> dict:
    """Pick the most up-to-date document from a duplicate group."""

    def sort_key(d: dict) -> tuple:
        status_rank = _STATUS_RANK.get(d.get("status", "scheduled"), 99)
        has_scores = 0 if (d.get("homeScore") is not None and d.get("awayScore") is not None) else 1
        last_updated = _parse_dt(d.get("lastUpdated")) or datetime.min.replace(tzinfo=UTC)
        return (status_rank, has_scores, -last_updated.timestamp())

    return sorted(docs, key=sort_key)[0]


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

    print(f"{'[DRY RUN] ' if not args.apply else ''}Fetching all match documents...")
    all_matches: list[dict] = list(
        container.query_items(
            query="SELECT * FROM c WHERE c.type = 'match'",
            enable_cross_partition_query=True,
        )
    )
    print(f"  Found {len(all_matches)} match documents.")

    # --- Phase 1: dedup by (homeTeamId, awayTeamId) ---
    by_pair: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for m in all_matches:
        key = (m.get("homeTeamId", ""), m.get("awayTeamId", ""))
        by_pair[key].append(m)

    dupes_deleted = 0
    for (_home, _away), docs in by_pair.items():
        if len(docs) < 2:
            continue
        keep = _best_doc(docs)
        for doc in docs:
            if doc["id"] == keep["id"]:
                continue
            print(
                f"  DEDUP  delete {doc['id']} ({doc.get('status')}, "
                f"score={doc.get('homeScore')}-{doc.get('awayScore')}) "
                f"-> keep {keep['id']} ({keep.get('status')}, "
                f"score={keep.get('homeScore')}-{keep.get('awayScore')})"
            )
            if args.apply:
                container.delete_item(item=doc["id"], partition_key="match")
            dupes_deleted += 1

    # --- Phase 2: fix stale "live" matches ---
    now = datetime.now(UTC)
    stale_fixed = 0
    for m in all_matches:
        if m.get("status") != "live":
            continue
        if m.get("homeScore") is None or m.get("awayScore") is None:
            continue
        scheduled_dt = _parse_dt(m.get("scheduledAt"))
        if scheduled_dt is None:
            continue
        if now - scheduled_dt <= timedelta(hours=3):
            continue
        print(
            f"  STALE  {m['id']} ({m.get('homeTeamId')} vs {m.get('awayTeamId')}, "
            f"score={m.get('homeScore')}-{m.get('awayScore')}, "
            f"scheduledAt={m.get('scheduledAt')}) -> set status=completed"
        )
        if args.apply:
            container.patch_item(
                item=m["id"],
                partition_key="match",
                patch_operations=[
                    {"op": "set", "path": "/status", "value": "completed"},
                    {"op": "set", "path": "/lastUpdated", "value": now.isoformat()},
                ],
            )
        stale_fixed += 1

    # --- Phase 3: find scheduled matches that should have scores by now ---
    print("\n--- Matches still 'scheduled' but past their kick-off + 3h ---")
    stale_scheduled_docs: list[dict] = []
    for m in all_matches:
        if m.get("status") != "scheduled":
            continue
        scheduled_dt = _parse_dt(m.get("scheduledAt"))
        if scheduled_dt is None:
            continue
        if now - scheduled_dt <= timedelta(hours=3):
            continue
        print(
            f"  STALE-SCHED  {m['id']} ({m.get('homeTeamId')} vs {m.get('awayTeamId')}, "
            f"scheduledAt={m.get('scheduledAt')}, source={m.get('source')})"
        )
        stale_scheduled_docs.append(m)
    if not stale_scheduled_docs:
        print("  (none)")

    stale_scheduled_ids = {
        (m.get("homeTeamId", ""), m.get("awayTeamId", "")) for m in stale_scheduled_docs
    }

    # --- Phase 4: attempt to heal stale-scheduled matches via TheSportsDB ---
    healed = 0
    if stale_scheduled_docs:
        healed = _heal_stale_scheduled(container, stale_scheduled_docs, args.apply)

    # --- Phase 5: TheSportsDB diagnostic for any that remain unfixed ---
    if stale_scheduled_ids:
        _diagnose_thesportsdb(stale_scheduled_ids)

    suffix = "" if args.apply else " (dry run -- use --apply to commit)"
    print(
        f"\nDone{suffix}: {dupes_deleted} duplicate(s) deleted, "
        f"{stale_fixed} stale 'live' match(es) fixed, "
        f"{len(stale_scheduled_docs)} stale 'scheduled' match(es) flagged, "
        f"{healed} healed via TheSportsDB."
    )


def _build_team_name_map(container) -> dict[str, str]:
    items = container.query_items(
        query="SELECT c.id, c.name FROM c WHERE c.type = 'team'",
        enable_cross_partition_query=True,
    )
    return {item["name"]: item["id"] for item in items}


def _heal_stale_scheduled(container, stale_docs: list[dict], apply: bool) -> int:
    """Attempt to fetch results from TheSportsDB by date for stale-scheduled matches."""
    import httpx

    api_key = os.environ.get("THESPORTSDB_API_KEY", "3")
    league_id = os.environ.get("THESPORTSDB_LEAGUE_ID", "4429")
    base = "https://www.thesportsdb.com/api/v1/json"

    name_to_id = _build_team_name_map(container)

    # Group stale docs by calendar date
    by_date: dict[str, list[dict]] = {}
    for m in stale_docs:
        date_key = (m.get("scheduledAt") or "")[:10]
        if date_key:
            by_date.setdefault(date_key, []).append(m)

    print(f"\n--- Phase 4: attempting TheSportsDB heal for {len(stale_docs)} match(es) ---")
    healed = 0

    for date_key, matches in by_date.items():
        try:
            resp = httpx.get(
                f"{base}/{api_key}/eventsday.php",
                params={"d": date_key, "s": "Soccer"},
                timeout=15.0,
            )
            resp.raise_for_status()
            events = [
                e
                for e in (resp.json().get("events") or [])
                if str(e.get("idLeague", "")) == str(league_id)
            ]
        except Exception as exc:
            print(f"  WARN  eventsday {date_key} failed: {exc}")
            continue

        # Index events by (homeTeamId, awayTeamId) after resolving names
        event_by_teams: dict[tuple[str, str], dict] = {}
        for e in events:
            h = name_to_id.get(e.get("strHomeTeam", ""), "")
            a = name_to_id.get(e.get("strAwayTeam", ""), "")
            if h and a:
                event_by_teams[(h, a)] = e

        for m in matches:
            key = (m.get("homeTeamId", ""), m.get("awayTeamId", ""))
            event = event_by_teams.get(key)
            if not event:
                print(
                    f"  NOT-FOUND  {m['id']} ({key[0]} vs {key[1]}) not in TheSportsDB for {date_key}"
                )
                continue

            raw_status = event.get("strStatus") or event.get("strProgress") or ""
            home_score_raw = event.get("intHomeScore")
            away_score_raw = event.get("intAwayScore")
            home_score = None if home_score_raw in (None, "") else int(home_score_raw)
            away_score = None if away_score_raw in (None, "") else int(away_score_raw)
            status = raw_status.lower().strip()
            if status in ("ft", "ap", "aet", "match finished"):
                status = "completed"
            elif home_score is not None and away_score is not None:
                status = "completed"
            else:
                status = "scheduled"

            if status != "completed":
                print(f"  SKIP  {m['id']}: TheSportsDB status={raw_status!r}, no scores yet")
                continue

            if home_score is None or away_score is None:
                print(f"  SKIP  {m['id']}: completed but missing scores on TheSportsDB")
                continue

            if home_score > away_score:
                winner_id = key[0]
            elif away_score > home_score:
                winner_id = key[1]
            else:
                winner_id = None

            now_iso = datetime.now(UTC).isoformat()
            print(
                f"  HEAL  {m['id']} ({key[0]} vs {key[1]}) "
                f"score={home_score}-{away_score} winner={winner_id} -> status=completed"
            )
            if apply:
                container.patch_item(
                    item=m["id"],
                    partition_key="match",
                    patch_operations=[
                        {"op": "set", "path": "/status", "value": "completed"},
                        {"op": "set", "path": "/homeScore", "value": home_score},
                        {"op": "set", "path": "/awayScore", "value": away_score},
                        {"op": "set", "path": "/winnerId", "value": winner_id},
                        {"op": "set", "path": "/lastUpdated", "value": now_iso},
                    ],
                )
            healed += 1

    return healed


def _diagnose_thesportsdb(missing_pairs: set[tuple[str, str]]) -> None:
    """Fetch TheSportsDB recent/next events and show what team names it uses,
    to diagnose why certain matches were never picked up by the sync."""
    import httpx

    api_key = os.environ.get("THESPORTSDB_API_KEY", "3")
    league_id = os.environ.get("THESPORTSDB_LEAGUE_ID", "4429")
    base = "https://www.thesportsdb.com/api/v1/json"

    print("\n--- TheSportsDB diagnostic (recent + next events) ---")
    events: list[dict] = []
    for endpoint in ("eventspastleague.php", "eventsnextleague.php"):
        try:
            resp = httpx.get(f"{base}/{api_key}/{endpoint}", params={"id": league_id}, timeout=15.0)
            resp.raise_for_status()
            events.extend(resp.json().get("events") or [])
        except Exception as exc:
            print(f"  WARN  {endpoint} failed: {exc}")

    if not events:
        print("  No events returned from TheSportsDB.")
        return

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    recent = [e for e in events if e.get("dateEvent", "") in (today, yesterday)]

    print(f"  Events on {yesterday} / {today} ({len(recent)} of {len(events)} total):")
    for e in recent:
        print(
            f"    id={e.get('idEvent')}  {e.get('strHomeTeam')} vs {e.get('strAwayTeam')}"
            f"  date={e.get('dateEvent')}  status={e.get('strStatus')!r}"
            f"  score={e.get('intHomeScore')}-{e.get('intAwayScore')}"
        )

    print("\n  All team names seen today/yesterday:")
    names = sorted({e.get("strHomeTeam") for e in recent} | {e.get("strAwayTeam") for e in recent})
    for n in names:
        print(f"    {n!r}")


if __name__ == "__main__":
    main()
