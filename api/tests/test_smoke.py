import os
from collections.abc import Iterator

import pytest

pytest.importorskip("azure.cosmos")

import api.cosmos as cosmos_module  # noqa: E402
from api.cosmos import get_container  # noqa: E402


def _require_real_cosmos() -> str:
    conn = os.environ.get("COSMOS_CONNECTION_STRING", "")
    if not conn or "localhost" in conn or "127.0.0.1" in conn:
        pytest.skip("real COSMOS_CONNECTION_STRING required")
    return conn


@pytest.fixture(autouse=True)
def reset_cosmos() -> Iterator[None]:
    cosmos_module.reset_container()
    yield
    cosmos_module.reset_container()


@pytest.mark.smoke
def test_cosmos_container_reachable() -> None:
    _require_real_cosmos()
    container = get_container()
    props = container.read()
    assert props["id"] == os.environ.get("COSMOS_CONTAINER_NAME", "items")


@pytest.mark.smoke
def test_cosmos_can_query_items() -> None:
    _require_real_cosmos()
    container = get_container()
    results = list(
        container.query_items(
            "SELECT TOP 1 c.id FROM c",
            enable_cross_partition_query=True,
        )
    )
    assert isinstance(results, list)
