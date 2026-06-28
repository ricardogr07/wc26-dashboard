"""One-shot: resolve R32 TBD_ placeholders and mark eliminated teams."""

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

# Official matchups (Sky Sports + FIFA.com, June 28 2026)
R32_PATCHES = [
    ("r32_74", "GER", "PAR"),
    ("r32_75", "NED", "MAR"),
    ("r32_76", "BRA", "JPN"),
    ("r32_77", "FRA", "SWE"),
    ("r32_78", "CIV", "NOR"),
    ("r32_79", "MEX", "ECU"),
    ("r32_80", "ENG", "COD"),
    ("r32_81", "USA", "BIH"),
    ("r32_82", "BEL", "SEN"),
    ("r32_83", "POR", "CRO"),
    ("r32_84", "ESP", "AUT"),
    ("r32_85", "SUI", "ALG"),
    ("r32_86", "ARG", "CPV"),
    ("r32_87", "COL", "GHA"),
    ("r32_88", "AUS", "EGY"),
]

QUALIFIED: frozenset[str] = frozenset(
    {
        "RSA",
        "CAN",
        "GER",
        "PAR",
        "NED",
        "MAR",
        "BRA",
        "JPN",
        "FRA",
        "SWE",
        "CIV",
        "NOR",
        "MEX",
        "ECU",
        "ENG",
        "COD",
        "USA",
        "BIH",
        "BEL",
        "SEN",
        "POR",
        "CRO",
        "ESP",
        "AUT",
        "SUI",
        "ALG",
        "ARG",
        "CPV",
        "COL",
        "GHA",
        "AUS",
        "EGY",
    }
)

conn = os.environ["COSMOS_CONNECTION_STRING"]
container = (
    CosmosClient.from_connection_string(conn)
    .get_database_client(os.environ.get("COSMOS_DATABASE_NAME", "wc26db"))
    .get_container_client(os.environ.get("COSMOS_CONTAINER_NAME", "items"))
)
now_iso = datetime.now(UTC).isoformat()

# 1 — patch R32 match documents
print("Patching R32 matches…")
for match_id, home, away in R32_PATCHES:
    container.patch_item(
        item=match_id,
        partition_key="match",
        patch_operations=[
            {"op": "set", "path": "/homeTeamId", "value": home},
            {"op": "set", "path": "/awayTeamId", "value": away},
            {"op": "set", "path": "/lastUpdated", "value": now_iso},
        ],
    )
    container.create_item(
        {
            "id": f"audit_{uuid.uuid4().hex}",
            "type": "audit",
            "action": "r32_team_patch",
            "matchId": match_id,
            "homeTeamId": home,
            "awayTeamId": away,
            "appliedAt": now_iso,
        }
    )
    print(f"  {match_id}: {home} vs {away}")

# 2 — eliminate teams that didn't qualify
print("\nMarking eliminated teams…")
all_teams = list(
    container.query_items(
        query="SELECT c.id, c.status FROM c WHERE c.type = 'team'",
        enable_cross_partition_query=True,
    )
)
eliminated = [t for t in all_teams if t["id"] not in QUALIFIED]
for team in eliminated:
    if team.get("status") == "eliminated":
        print(f"  {team['id']} already eliminated, skip")
        continue
    container.patch_item(
        item=team["id"],
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
            "teamId": team["id"],
            "appliedAt": now_iso,
        }
    )
    print(f"  {team['id']} -> eliminated")

print(f"\nDone — {len(R32_PATCHES)} matches patched, {len(eliminated)} teams eliminated.")
