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


@pytest.mark.smoke
def test_standings_returns_five_participants() -> None:
    import json
    import unittest.mock as mock

    _require_real_cosmos()
    from api.handlers.standings import handle_standings

    req = mock.MagicMock()
    resp = handle_standings(req)
    data = json.loads(resp.get_body())
    assert len(data["standings"]) == 5, f"expected 5 standings entries, got: {data['standings']}"


@pytest.mark.smoke
def test_matches_returns_fixtures() -> None:
    import json
    import unittest.mock as mock

    _require_real_cosmos()
    from api.handlers.matches import handle_matches

    req = mock.MagicMock()
    req.params = {}
    resp = handle_matches(req)
    data = json.loads(resp.get_body())
    count = len(data["matches"])
    assert count >= 72, f"expected >= 72 match fixtures, got {count}"


@pytest.mark.smoke
def test_health_returns_ok() -> None:
    import unittest.mock as mock

    _require_real_cosmos()
    import function_app

    req = mock.MagicMock()
    resp = function_app.health(req)
    assert resp.status_code == 200
    assert resp.get_body() == b"ok"


@pytest.mark.smoke
def test_simulate_returns_data() -> None:
    import json
    import unittest.mock as mock

    _require_real_cosmos()
    from api.handlers.simulate import handle_simulate

    req = mock.MagicMock()
    req.get_json.return_value = {}
    resp = handle_simulate(req)
    assert resp.status_code == 200, f"simulate returned {resp.status_code}: {resp.get_body()[:200]}"
    data = json.loads(resp.get_body())
    assert "probabilities" in data, (
        f"missing 'probabilities' key in simulate response: {list(data.keys())}"
    )
    assert len(data["probabilities"]) > 0, "simulate returned empty probabilities"
