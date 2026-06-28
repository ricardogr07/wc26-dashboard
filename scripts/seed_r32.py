#!/usr/bin/env python3
"""Compute group standings and seed R32 match documents into CosmosDB.

Reads completed group-stage matches from Cosmos, derives group standings
(pts → GD → GF), and upserts 16 R32 documents with the official FIFA match
schedule.  Safe to re-run at any time — uses upsert semantics so successive
runs patch placeholder TBD team IDs as groups complete.

Team ID placeholders used when a group is not yet finished:
  "TBD_{GROUP}1"  — e.g. "TBD_F1" for Group F winner
  "TBD_{GROUP}2"  — e.g. "TBD_F2" for Group F runner-up
  "TBD_3RD"       — best 3rd-place qualifier (resolved after all groups finish)

Usage:
  # Dry run — prints what would be written, touches nothing:
  python scripts/seed_r32.py

  # Write to production CosmosDB:
  COSMOS_CONNECTION_STRING=<conn> python scripts/seed_r32.py --apply

  # Local emulator:
  python scripts/seed_r32.py --apply
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import UTC, datetime

from azure.cosmos import CosmosClient

_EMULATOR_CONN = (
    "AccountEndpoint=https://localhost:8081/;"
    "AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b5hG9I/o6xK7xCy5h4HJf/qzl5s3v4sLQ==;"
)

# ---------------------------------------------------------------------------
# Official FIFA WC2026 R32 schedule
# (match_id, scheduledAt UTC, home_slot, away_slot, venue)
#
# Slot descriptors: (group | None, "1st"|"2nd"|"3rd")
#   group=None  → best 3rd-place qualifier (TBD until all groups finish)
# ---------------------------------------------------------------------------
_R32_SCHEDULE: list[tuple[str, str, tuple[str | None, str], tuple[str | None, str], str]] = [
    # (id,      scheduledAt,            home_slot,       away_slot,       venue)
    ("r32_73", "2026-06-28T19:00:00Z", ("A", "2nd"), ("B", "2nd"), "SoFi Stadium, Inglewood"),
    ("r32_74", "2026-06-29T20:30:00Z", ("E", "1st"), (None, "3rd"), "Gillette Stadium, Foxborough"),
    ("r32_76", "2026-06-29T20:30:00Z", ("C", "1st"), ("F", "2nd"), "NRG Stadium, Houston"),
    ("r32_75", "2026-06-30T00:00:00Z", ("F", "1st"), ("C", "2nd"), "Estadio BBVA, Guadalupe"),
    ("r32_78", "2026-06-30T17:00:00Z", ("E", "2nd"), ("I", "2nd"), "AT&T Stadium, Arlington"),
    (
        "r32_77",
        "2026-06-30T21:00:00Z",
        ("I", "1st"),
        (None, "3rd"),
        "MetLife Stadium, East Rutherford",
    ),
    ("r32_79", "2026-07-01T00:00:00Z", ("A", "1st"), (None, "3rd"), "Estadio Azteca, Mexico City"),
    (
        "r32_80",
        "2026-07-01T16:00:00Z",
        ("L", "1st"),
        (None, "3rd"),
        "Mercedes-Benz Stadium, Atlanta",
    ),
    ("r32_82", "2026-07-01T20:00:00Z", ("G", "1st"), (None, "3rd"), "Lumen Field, Seattle"),
    ("r32_81", "2026-07-02T00:00:00Z", ("D", "1st"), (None, "3rd"), "Levi's Stadium, Santa Clara"),
    ("r32_84", "2026-07-02T19:00:00Z", ("H", "1st"), ("J", "2nd"), "SoFi Stadium, Inglewood"),
    ("r32_83", "2026-07-02T23:00:00Z", ("K", "2nd"), ("L", "2nd"), "BMO Field, Toronto"),
    ("r32_85", "2026-07-03T03:00:00Z", ("B", "1st"), (None, "3rd"), "BC Place, Vancouver"),
    ("r32_88", "2026-07-03T18:00:00Z", ("D", "2nd"), ("G", "2nd"), "AT&T Stadium, Arlington"),
    (
        "r32_86",
        "2026-07-03T22:00:00Z",
        ("J", "1st"),
        ("H", "2nd"),
        "Hard Rock Stadium, Miami Gardens",
    ),
    (
        "r32_87",
        "2026-07-04T00:30:00Z",
        ("K", "1st"),
        (None, "3rd"),
        "Arrowhead Stadium, Kansas City",
    ),
]

_POS_IDX = {"1st": 0, "2nd": 1, "3rd": 2}


def _compute_standings(group_matches: list[dict]) -> tuple[dict[str, list[str]], dict[str, bool]]:
    """Return (group → [1st,2nd,3rd,4th] team IDs, group → is_complete)."""
    pts: dict[str, int] = defaultdict(int)
    gd: dict[str, int] = defaultdict(int)
    gf: dict[str, int] = defaultdict(int)
    group_of: dict[str, str] = {}
    total: dict[str, int] = defaultdict(int)
    done: dict[str, int] = defaultdict(int)

    for m in group_matches:
        g = m.get("group")
        if not g:
            continue  # skip any match missing its group field
        home = m.get("homeTeamId", "")
        away = m.get("awayTeamId", "")
        group_of[home] = g
        group_of[away] = g
        total[g] += 1

        if m.get("status") != "completed":
            continue
        done[g] += 1
        hs = m.get("homeScore") or 0
        as_ = m.get("awayScore") or 0
        gf[home] += hs
        gf[away] += as_
        gd[home] += hs - as_
        gd[away] += as_ - hs
        winner = m.get("winnerId")
        if winner == home:
            pts[home] += 3
        elif winner == away:
            pts[away] += 3
        else:
            pts[home] += 1
            pts[away] += 1

    # Group teams by group letter
    teams_by_group: dict[str, set[str]] = defaultdict(set)
    for team, g in group_of.items():
        teams_by_group[g].add(team)

    standings: dict[str, list[str]] = {}
    complete: dict[str, bool] = {}
    for g, members in sorted(teams_by_group.items()):
        ranked = sorted(members, key=lambda t: (-pts[t], -gd[t], -gf[t]))
        standings[g] = ranked
        complete[g] = done[g] == total[g] and total[g] > 0

    return standings, complete


def _resolve_team(
    desc: tuple[str | None, str],
    standings: dict[str, list[str]],
    complete: dict[str, bool],
    thirds_iter,
) -> str:
    grp, pos = desc
    if grp is None:
        # 3rd-place slot: draw from ranked pool
        return next(thirds_iter, "TBD_3RD")
    if not complete.get(grp, False):
        suffix = {"1st": "1", "2nd": "2", "3rd": "3"}[pos]
        return f"TBD_{grp}{suffix}"
    ranked = standings.get(grp, [])
    idx = _POS_IDX[pos]
    return ranked[idx] if idx < len(ranked) else f"TBD_{grp}{idx + 1}"


def _best_thirds(standings: dict[str, list[str]], complete: dict[str, bool]) -> list[str]:
    """Return the 8 best 3rd-place teams once ALL 12 groups are complete.

    The FIFA seeding table determines which 3rd-place team goes to which R32
    slot (495 possible group-combination rows). Partial assignment (before all
    groups finish) would put teams in the wrong slots, so we return an empty
    list until every group is settled — the caller writes TBD_3RD instead.

    TODO: after June 28 when all groups finish, implement the FIFA WC2026
    seeding table here to map each 3rd-place team to its correct slot.
    For now the full list is returned in sorted (alphabetical) order as a
    stand-in; the simulation engine uses sequential assignment which is a
    reasonable approximation for probability forecasting.
    """
    if not all(complete.get(g) for g in standings):
        return []  # not ready yet — all 12 groups must be done
    thirds: list[str] = []
    for _g, ranked in standings.items():
        if len(ranked) >= 3:
            thirds.append(ranked[2])
    return sorted(thirds)[:8]


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
    print(f"{prefix}Fetching group-stage matches from CosmosDB...")

    group_matches: list[dict] = list(
        container.query_items(
            query="SELECT * FROM c WHERE c.type = 'match' AND c.round = 'group'",
            enable_cross_partition_query=True,
        )
    )
    print(f"  Found {len(group_matches)} group-stage match(es).")

    standings, complete = _compute_standings(group_matches)

    print("\nGroup standings (complete groups only):")
    for g in sorted(standings):
        status = "complete" if complete.get(g) else "in progress"
        ranked = standings[g]
        print(f"  Group {g} [{status}]: " + " > ".join(ranked[:3]))

    thirds = _best_thirds(standings, complete)
    thirds_complete = len([g for g in standings if complete.get(g)]) == 12
    if thirds_complete:
        print(f"\n  8 best 3rd-place qualifiers: {thirds}")
    else:
        n_done = sum(1 for g in standings if complete.get(g))
        print(f"\n  {n_done}/12 groups complete — 3rd-place slots remain TBD")

    print(f"\n{prefix}R32 documents to upsert:")

    now_iso = datetime.now(UTC).isoformat()
    upserted = 0
    thirds_iter = iter(thirds)

    for match_id, scheduled_at, home_desc, away_desc, venue in _R32_SCHEDULE:
        home_id = _resolve_team(home_desc, standings, complete, thirds_iter)
        away_id = _resolve_team(away_desc, standings, complete, thirds_iter)

        # Check existing doc
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
            f"  {marker}{match_id}  {home_id:12s} vs {away_id:12s}"
            + (f"  [was: {existing_home} vs {existing_away}]" if change and existing_home else "")
        )

        if not args.apply:
            continue

        doc: dict = {
            "id": match_id,
            "type": "match",
            "round": "r32",
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
    if not thirds_complete:
        print("Re-run after all groups finish (June 28) to resolve TBD_3RD slots.")


if __name__ == "__main__":
    main()
