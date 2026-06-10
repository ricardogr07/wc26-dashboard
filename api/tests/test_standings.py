from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import azure.functions as func

from api.handlers.standings import handle_standings


def _req() -> func.HttpRequest:
    return func.HttpRequest(
        method="GET",
        url="http://localhost:7071/api/standings",
        body=b"",
        headers={},
        params={},
    )


def _participant(id: str, display_name: str, team_ids: list[str]) -> dict:
    return {"id": id, "type": "participant", "displayName": display_name, "teamIds": team_ids}


def _team(
    id: str, name: str, group: str = "A", elo_rating: float = 1700.0, status: str = "active"
) -> dict:
    return {
        "id": id,
        "type": "team",
        "name": name,
        "group": group,
        "eloRating": elo_rating,
        "status": status,
    }


def _match(
    id: str,
    round: str,
    home_team_id: str,
    away_team_id: str,
    status: str = "scheduled",
    winner_id: str | None = None,
    home_score: int | None = None,
    away_score: int | None = None,
    group: str | None = None,
) -> dict:
    return {
        "id": id,
        "type": "match",
        "round": round,
        "group": group,
        "homeTeamId": home_team_id,
        "awayTeamId": away_team_id,
        "scheduledAt": "2026-06-15T19:00:00Z",
        "source": "thesportsdb",
        "lastUpdated": "2026-06-09T12:00:00Z",
        "status": status,
        "winnerId": winner_id,
        "homeScore": home_score,
        "awayScore": away_score,
    }


def _mock_container(participants: list, matches: list, teams: list) -> MagicMock:
    mock = MagicMock()

    def side_effect(query, **kwargs):
        if "type = 'participant'" in query:
            return iter(participants)
        if "type = 'match'" in query:
            return iter(matches)
        if "type = 'team'" in query:
            return iter(teams)
        return iter([])

    mock.query_items.side_effect = side_effect
    return mock


@patch("api.handlers.standings.get_container")
def test_standings_returns_all_participants(mock_gc: MagicMock) -> None:
    participants = [
        _participant("alice", "Alice", ["ESP", "ARG"]),
        _participant("bob", "Bob", ["MEX", "BRA"]),
    ]
    teams = [
        _team("ESP", "Spain"),
        _team("ARG", "Argentina"),
        _team("MEX", "Mexico"),
        _team("BRA", "Brazil"),
    ]
    mock_gc.return_value = _mock_container(participants, [], teams)

    resp = handle_standings(_req())

    assert resp.status_code == 200
    data = json.loads(resp.get_body())
    ids = [s["participantId"] for s in data["standings"]]
    assert set(ids) == {"alice", "bob"}


@patch("api.handlers.standings.get_container")
def test_standings_zero_scores_no_matches(mock_gc: MagicMock) -> None:
    participants = [_participant("alice", "Alice", ["ESP"])]
    teams = [_team("ESP", "Spain")]
    mock_gc.return_value = _mock_container(participants, [], teams)

    resp = handle_standings(_req())

    assert resp.status_code == 200
    data = json.loads(resp.get_body())
    assert data["standings"][0]["score"] == 0
    assert data["standings"][0]["rank"] == 1


@patch("api.handlers.standings.get_container")
def test_standings_group_qualification_points(mock_gc: MagicMock) -> None:
    # ESP owner = alice; r32 match → ESP qualifies → alice gets 1 pt
    participants = [_participant("alice", "Alice", ["ESP"])]
    teams = [_team("ESP", "Spain"), _team("GER", "Germany")]
    matches = [_match("m1", "r32", "ESP", "GER")]
    mock_gc.return_value = _mock_container(participants, matches, teams)

    resp = handle_standings(_req())

    data = json.loads(resp.get_body())
    assert data["standings"][0]["score"] == 1


@patch("api.handlers.standings.get_container")
def test_standings_knockout_win_points(mock_gc: MagicMock) -> None:
    # BRA owner = bob; BRA wins sf → 8 pts
    participants = [
        _participant("alice", "Alice", ["ESP"]),
        _participant("bob", "Bob", ["BRA"]),
    ]
    teams = [_team("ESP", "Spain"), _team("BRA", "Brazil")]
    matches = [
        _match(
            "m1",
            "sf",
            "BRA",
            "ESP",
            status="completed",
            winner_id="BRA",
            home_score=1,
            away_score=0,
        ),
    ]
    mock_gc.return_value = _mock_container(participants, matches, teams)

    resp = handle_standings(_req())

    data = json.loads(resp.get_body())
    standings_by_id = {s["participantId"]: s for s in data["standings"]}
    assert standings_by_id["bob"]["score"] == 8
    assert standings_by_id["alice"]["score"] == 0
    assert standings_by_id["bob"]["rank"] == 1
    assert standings_by_id["alice"]["rank"] == 2


@patch("api.handlers.standings.get_container")
def test_standings_ties_share_rank(mock_gc: MagicMock) -> None:
    participants = [
        _participant("alice", "Alice", ["ESP"]),
        _participant("bob", "Bob", ["BRA"]),
        _participant("carol", "Carol", ["MEX"]),
    ]
    # ESP and BRA in r32 → alice and bob each get 1pt; carol's MEX not in r32 → 0pt
    teams = [
        _team("ESP", "Spain"),
        _team("BRA", "Brazil"),
        _team("MEX", "Mexico"),
        _team("GER", "Germany"),
        _team("POL", "Poland"),
    ]
    matches = [
        _match("m1", "r32", "ESP", "GER"),  # alice +1, GER unowned
        _match("m2", "r32", "BRA", "POL"),  # bob +1, POL unowned; carol's MEX absent
    ]
    mock_gc.return_value = _mock_container(participants, matches, teams)

    resp = handle_standings(_req())

    data = json.loads(resp.get_body())
    standings_by_id = {s["participantId"]: s for s in data["standings"]}
    assert standings_by_id["alice"]["rank"] == standings_by_id["bob"]["rank"] == 1
    assert standings_by_id["carol"]["rank"] == 3


@patch("api.handlers.standings.get_container")
def test_standings_includes_team_details(mock_gc: MagicMock) -> None:
    participants = [_participant("alice", "Alice", ["ESP"])]
    teams = [_team("ESP", "Spain", group="B", elo_rating=2172.0, status="active")]
    mock_gc.return_value = _mock_container(participants, [], teams)

    resp = handle_standings(_req())

    data = json.loads(resp.get_body())
    team_entry = data["standings"][0]["teams"][0]
    assert team_entry["teamId"] == "ESP"
    assert team_entry["name"] == "Spain"
    assert team_entry["group"] == "B"
    assert team_entry["eloRating"] == 2172.0
    assert team_entry["status"] == "active"


@patch("api.handlers.standings.get_container")
def test_standings_cosmos_error_returns_500(mock_gc: MagicMock) -> None:
    mock_gc.side_effect = RuntimeError("connection failed")

    resp = handle_standings(_req())

    assert resp.status_code == 500
