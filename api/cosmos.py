from __future__ import annotations

import os

from azure.cosmos import ContainerProxy, CosmosClient

_container: ContainerProxy | None = None


def get_container() -> ContainerProxy:
    """Return the shared Cosmos DB container client, initializing it on first call."""
    global _container
    if _container is None:
        conn = os.environ["COSMOS_CONNECTION_STRING"]
        db = os.environ.get("COSMOS_DATABASE_NAME", "wc26db")
        ctr = os.environ.get("COSMOS_CONTAINER_NAME", "items")
        _container = (
            CosmosClient.from_connection_string(conn)
            .get_database_client(db)
            .get_container_client(ctr)
        )
    return _container


def reset_container() -> None:
    global _container
    _container = None
