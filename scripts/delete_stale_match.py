"""One-off script: delete the 2022 WC Final (ARG vs FRA) that was wrongly
synced into the 2026 Cosmos container.

Usage:
  COSMOS_CONNECTION_STRING="..." python scripts/delete_stale_match.py
  # or set it in api/local.settings.json and export it first
"""

import os
import sys

from azure.cosmos import CosmosClient

MATCH_ID = "tsdb_1666948"
PARTITION_KEY = "match"

conn_str = os.environ.get("COSMOS_CONNECTION_STRING")
if not conn_str:
    sys.exit("Set COSMOS_CONNECTION_STRING before running this script.")

db_name = os.environ.get("COSMOS_DATABASE_NAME", "wc26db")
container_name = os.environ.get("COSMOS_CONTAINER_NAME", "items")

client = CosmosClient.from_connection_string(conn_str)
container = client.get_database_client(db_name).get_container_client(container_name)

try:
    container.delete_item(item=MATCH_ID, partition_key=PARTITION_KEY)
    print(f"Deleted {MATCH_ID} ✓")
except Exception as e:
    print(f"Failed: {e}")
