from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import azure.functions as func

from api.handlers.matches import handle_matches


def _req(params: dict[str, str] | None = None) -> func.HttpRequest:
    return func.HttpRequest(
        method="GET",
        url="http://localhost:7071/api/matches",
        body=b"",
        headers={},
        params=params or {},
    )


def _team(id: str, name: str, elo_rating: float = 1700.0) -> dict:
    return {
        "id": id,
        "type": "team",
        "name": name,
        "group": "A",
        "eloRating": elo_rating,
        "status": "active",
    }


def _match(
    id: str,
    round: str = "group",
    home_team_id: str = "MEX",
    away_team_id: str = "POL",
    scheduled_at: str = "2026-06-15T19:00:00Z",
    status: str = "scheduled",
) -> dict:
    return {
        "id": id,
        "type": "match",
        "round": round,
        "group": "C",
        "homeTeamId": home_team_id,
        "awayTeamId": away_team_id,
        "scheduledAt": scheduled_at,
        "source": "thesportsdb",
        "lastUpdated": "2026-06-09T12:00:00Z",
        "status": status,
        "homeScore": None,
        "awayScore": None,
        "winnerId": None,
    }


def _mock_container(matches: list, teams: list) -> MagicMock:
    mock = MagicMock()

    def side_effect(query, **kwargs):
        if "type = 'team'" in query:
            return iter(teams)
        return iter(matches)

    mock.query_items.side_effect = side_effect
    return mock


@patch("api.handlers.matches.get_container")
def test_matches_no_filter_returns_all(mock_gc: MagicMock) -> None:
    matches = [_match("m1"), _match("m2", round="r32")]
    teams = [_team("MEX", "Mexico"), _team("POL", "Poland")]
    mock_gc.return_value = _mock_container(matches, teams)

    resp = handle_matches(_req())

    assert resp.status_code == 200
    data = json.loads(resp.get_body())
    assert len(data["matches"]) == 2


@patch("api.handlers.matches.get_container")
def test_matches_filter_by_round(mock_gc: MagicMock) -> None:
    group_match = _match("m1", round="group")
    mock_gc.return_value = _mock_container(
        [group_match], [_team("MEX", "Mexico"), _team("POL", "Poland")]
    )

    resp = handle_matches(_req({"round": "group"}))

    assert resp.status_code == 200
    # Verify the query included the round filter
    call_args = mock_gc.return_value.query_items.call_args_list[0]
    assert "c.round = @round" in call_args.kwargs["query"]
    assert any(
        p["name"] == "@round" and p["value"] == "group" for p in call_args.kwargs["parameters"]
    )


@patch("api.handlers.matches.get_container")
def test_matches_filter_by_date(mock_gc: MagicMock) -> None:
    mock_gc.return_value = _mock_container(
        [_match("m1", scheduled_at="2026-06-15T19:00:00Z")],
        [_team("MEX", "Mexico"), _team("POL", "Poland")],
    )

    resp = handle_matches(_req({"date": "2026-06-15"}))

    assert resp.status_code == 200
    call_args = mock_gc.return_value.query_items.call_args_list[0]
    assert "STARTSWITH" in call_args.kwargs["query"]
    assert any(
        p["name"] == "@date" and p["value"] == "2026-06-15" for p in call_args.kwargs["parameters"]
    )


@patch("api.handlers.matches.get_container")
def test_matches_invalid_round_returns_400(mock_gc: MagicMock) -> None:
    resp = handle_matches(_req({"round": "quarters"}))

    assert resp.status_code == 400
    mock_gc.assert_not_called()


@patch("api.handlers.matches.get_container")
def test_matches_invalid_date_returns_400(mock_gc: MagicMock) -> None:
    resp = handle_matches(_req({"date": "not-a-date"}))

    assert resp.status_code == 400
    mock_gc.assert_not_called()


@patch("api.handlers.matches.get_container")
def test_matches_team_names_resolved(mock_gc: MagicMock) -> None:
    teams = [_team("MEX", "Mexico", 1680.0), _team("POL", "Poland", 1750.0)]
    mock_gc.return_value = _mock_container([_match("m1")], teams)

    resp = handle_matches(_req())

    data = json.loads(resp.get_body())
    m = data["matches"][0]
    assert m["homeTeam"]["name"] == "Mexico"
    assert m["homeTeam"]["eloRating"] == 1680.0
    assert m["awayTeam"]["name"] == "Poland"
    assert m["awayTeam"]["eloRating"] == 1750.0


@patch("api.handlers.matches.get_container")
def test_matches_sorted_by_scheduled_at(mock_gc: MagicMock) -> None:
    matches = [
        _match("m2", scheduled_at="2026-06-16T19:00:00Z"),
        _match("m1", scheduled_at="2026-06-15T19:00:00Z"),
    ]
    teams = [_team("MEX", "Mexico"), _team("POL", "Poland")]
    mock_gc.return_value = _mock_container(matches, teams)

    resp = handle_matches(_req())

    data = json.loads(resp.get_body())
    assert data["matches"][0]["id"] == "m1"
    assert data["matches"][1]["id"] == "m2"


@patch("api.handlers.matches.get_container")
def test_matches_cosmos_error_returns_500(mock_gc: MagicMock) -> None:
    mock_gc.side_effect = RuntimeError("connection failed")

    resp = handle_matches(_req())

    assert resp.status_code == 500
