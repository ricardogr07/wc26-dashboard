from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import azure.functions as func
import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from api.handlers.admin_override import handle_admin_override

_VALID_KEY = "test-secret-key"

_MATCH_DOC = {
    "id": "match_001",
    "type": "match",
    "homeTeamId": "MEX",
    "awayTeamId": "POL",
}


def _req(
    body: dict | None = None,
    key: str | None = _VALID_KEY,
) -> func.HttpRequest:
    raw = json.dumps(body or {}).encode()
    return func.HttpRequest(
        method="POST",
        url="http://localhost:7071/api/admin/override",
        body=raw,
        headers={"x-functions-key": key} if key else {},
        params={},
    )


def _valid_body() -> dict:
    return {"matchId": "match_001", "homeScore": 2, "awayScore": 1, "winnerId": "MEX"}


@pytest.fixture(autouse=True)
def _set_admin_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", _VALID_KEY)


@patch("api.handlers.admin_override.get_container")
def test_override_missing_key_returns_401(mock_gc: MagicMock) -> None:
    resp = handle_admin_override(_req(key=None))

    assert resp.status_code == 401
    mock_gc.assert_not_called()


@patch("api.handlers.admin_override.get_container")
def test_override_wrong_key_returns_401(mock_gc: MagicMock) -> None:
    resp = handle_admin_override(_req(body=_valid_body(), key="wrong-key"))

    assert resp.status_code == 401
    mock_gc.assert_not_called()


@patch("api.handlers.admin_override.get_container")
def test_override_missing_body_fields_returns_400(mock_gc: MagicMock) -> None:
    resp = handle_admin_override(_req(body={"matchId": "match_001"}))

    assert resp.status_code == 400
    mock_gc.assert_not_called()


@patch("api.handlers.admin_override.get_container")
def test_override_negative_score_returns_400(mock_gc: MagicMock) -> None:
    body = {**_valid_body(), "homeScore": -1}
    resp = handle_admin_override(_req(body=body))

    assert resp.status_code == 400
    mock_gc.assert_not_called()


@patch("api.handlers.admin_override.get_container")
def test_override_invalid_winner_returns_400(mock_gc: MagicMock) -> None:
    mock_container = MagicMock()
    mock_container.read_item.return_value = _MATCH_DOC
    mock_gc.return_value = mock_container

    body = {**_valid_body(), "winnerId": "BRA"}  # BRA is not in this match
    resp = handle_admin_override(_req(body=body))

    assert resp.status_code == 400


@patch("api.handlers.admin_override.get_container")
def test_override_match_not_found_returns_404(mock_gc: MagicMock) -> None:
    mock_container = MagicMock()
    mock_container.read_item.side_effect = CosmosResourceNotFoundError(404, "not found")
    mock_gc.return_value = mock_container

    resp = handle_admin_override(_req(body=_valid_body()))

    assert resp.status_code == 404


@patch("api.handlers.admin_override.get_container")
def test_override_success_patches_match(mock_gc: MagicMock) -> None:
    mock_container = MagicMock()
    mock_container.read_item.return_value = _MATCH_DOC
    mock_gc.return_value = mock_container

    resp = handle_admin_override(_req(body=_valid_body()))

    assert resp.status_code == 200
    data = json.loads(resp.get_body())
    assert data["matchId"] == "match_001"
    assert data["status"] == "updated"

    mock_container.patch_item.assert_called_once()
    patch_call = mock_container.patch_item.call_args
    assert patch_call.kwargs["item"] == "match_001"
    assert patch_call.kwargs["partition_key"] == "match"
    ops = patch_call.kwargs["patch_operations"]
    paths = {op["path"]: op["value"] for op in ops}
    assert paths["/homeScore"] == 2
    assert paths["/awayScore"] == 1
    assert paths["/winnerId"] == "MEX"
    assert paths["/status"] == "completed"


@patch("api.handlers.admin_override.get_container")
def test_override_success_writes_audit_log(mock_gc: MagicMock) -> None:
    mock_container = MagicMock()
    mock_container.read_item.return_value = _MATCH_DOC
    mock_gc.return_value = mock_container

    handle_admin_override(_req(body=_valid_body()))

    mock_container.create_item.assert_called_once()
    audit_doc = mock_container.create_item.call_args.args[0]
    assert audit_doc["type"] == "audit"
    assert audit_doc["action"] == "override"
    assert audit_doc["matchId"] == "match_001"
    assert audit_doc["homeScore"] == 2
    assert audit_doc["awayScore"] == 1
    assert audit_doc["winnerId"] == "MEX"
    assert audit_doc["id"].startswith("audit_")


@patch("api.handlers.admin_override.get_container")
def test_override_cosmos_error_returns_500(mock_gc: MagicMock) -> None:
    mock_gc.side_effect = RuntimeError("connection failed")

    resp = handle_admin_override(_req(body=_valid_body()))

    assert resp.status_code == 500
