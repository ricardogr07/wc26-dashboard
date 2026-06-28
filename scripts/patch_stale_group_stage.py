"""One-shot: patch 4 group-stage matches that fell off the TSDB sync window."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Load .env.local so this works without export-ing vars
for line in (Path(__file__).parents[1] / ".env.local").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from azure.cosmos import CosmosClient  # noqa: E402

PATCHES = [
    # (match_id, home_score, away_score, winner_id)
    ("wiki_F3_2", 1, 3, "NED"),  # TUN 1-3 NED
    ("wiki_L3_2", 2, 1, "CRO"),  # CRO 2-1 GHA
    ("wiki_K3_1", 0, 0, None),  # COL 0-0 POR  (draw)
    ("wiki_K3_2", 3, 1, "COD"),  # COD 3-1 UZB
]

conn = os.environ["COSMOS_CONNECTION_STRING"]
db = os.environ.get("COSMOS_DATABASE_NAME", "wc26db")
ctr = os.environ.get("COSMOS_CONTAINER_NAME", "items")

container = (
    CosmosClient.from_connection_string(conn).get_database_client(db).get_container_client(ctr)
)
now_iso = datetime.now(UTC).isoformat()

for match_id, home_score, away_score, winner_id in PATCHES:
    container.patch_item(
        item=match_id,
        partition_key="match",
        patch_operations=[
            {"op": "set", "path": "/status", "value": "completed"},
            {"op": "set", "path": "/homeScore", "value": home_score},
            {"op": "set", "path": "/awayScore", "value": away_score},
            {"op": "set", "path": "/winnerId", "value": winner_id},
            {"op": "set", "path": "/lastUpdated", "value": now_iso},
        ],
    )
    container.create_item(
        {
            "id": f"audit_{uuid.uuid4().hex}",
            "type": "audit",
            "action": "manual_patch",
            "matchId": match_id,
            "homeScore": home_score,
            "awayScore": away_score,
            "winnerId": winner_id,
            "appliedAt": now_iso,
        }
    )
    print(f"  patched {match_id}: {home_score}-{away_score}  winner={winner_id}")

print("done")
