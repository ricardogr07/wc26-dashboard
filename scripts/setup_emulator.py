#!/usr/bin/env python3
"""Create the wc26db database and items container on the local Cosmos emulator.

Run once after `docker compose up --wait`:
    python scripts/setup_emulator.py
"""
import os

from azure.cosmos import CosmosClient, PartitionKey

EMULATOR_CONN = (
    "AccountEndpoint=https://localhost:8081/;"
    "AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b5hG9I/o6xK7xCy5h4HJf/qzl5s3v4sLQ==;"
)

conn = os.environ.get("COSMOS_CONNECTION_STRING", EMULATOR_CONN)
db_name = os.environ.get("COSMOS_DATABASE_NAME", "wc26db")
ctr_name = os.environ.get("COSMOS_CONTAINER_NAME", "items")

verify_ssl = "localhost" not in conn and "127.0.0.1" not in conn
client = CosmosClient.from_connection_string(conn, connection_verify=verify_ssl)
db = client.create_database_if_not_exists(db_name)
container = db.create_container_if_not_exists(
    id=ctr_name,
    partition_key=PartitionKey(path="/type"),
)
print(f"Ready: {db_name}/{ctr_name} (id={container.id})")
