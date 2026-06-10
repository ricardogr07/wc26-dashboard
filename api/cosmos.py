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
        # Disable TLS verification for the local emulator (self-signed cert)
        verify_ssl = "localhost" not in conn and "127.0.0.1" not in conn
        _container = (
            CosmosClient.from_connection_string(conn, connection_verify=verify_ssl)
            .get_database_client(db)
            .get_container_client(ctr)
        )
    return _container


def reset_container() -> None:
    global _container
    _container = None
