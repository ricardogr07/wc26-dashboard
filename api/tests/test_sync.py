from __future__ import annotations

from unittest.mock import MagicMock, patch

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from api.sync_matches.elo_updater import compute_elo_update
from api.sync_matches.thesportsdb import (
    fetch_live_and_recent_events,
    parse_round,
    parse_scheduled_at,
    parse_score,
    parse_status,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEAM_NAME_MAP = {
    "Mexico": "MEX",
    "South Africa": "RSA",
    "Argentina": "ARG",
    "Brazil": "BRA",
}

_SCHEDULED_EVENT: dict = {
    "idEvent": "2391728",
    "strHomeTeam": "Mexico",
    "strAwayTeam": "South Africa",
    "dateEvent": "2026-06-11",
    "strTime": "19:00:00",
    "strStatus": "",
    "strProgress": "",
    "intHomeScore": None,
    "intAwayScore": None,
    "strWinner": "",
    "strVenue": "Estadio Azteca",
    "strRound": "1",
}

_COMPLETED_EVENT: dict = {
    **_SCHEDULED_EVENT,
    "strStatus": "Match Finished",
    "intHomeScore": "2",
    "intAwayScore": "1",
    "strWinner": "Mexico",
}

_DRAW_EVENT: dict = {
    **_SCHEDULED_EVENT,
    "strStatus": "Match Finished",
    "intHomeScore": "1",
    "intAwayScore": "1",
    "strWinner": "",
}

_EXISTING_SCHEDULED_DOC: dict = {
    "id": "tsdb_2391728",
    "type": "match",
    "round": "group",
    "group": "A",
    "homeTeamId": "MEX",
    "awayTeamId": "RSA",
    "scheduledAt": "2026-06-11T19:00:00+00:00",
    "status": "scheduled",
    "homeScore": None,
    "awayScore": None,
    "winnerId": None,
    "source": "thesportsdb",
    "lastUpdated": "2026-06-09T00:00:00+00:00",
}


def _timer() -> func.TimerRequest:
    return MagicMock(spec=func.TimerRequest)


def _mock_container(read_side_effect=None, query_result=None):
    container = MagicMock()
    if read_side_effect is not None:
        container.read_item.side_effect = read_side_effect
    if query_result is not None:
        container.query_items.return_value = iter(query_result)
    return container


# ---------------------------------------------------------------------------
# parse_score
# ---------------------------------------------------------------------------


def test_parse_score_none_returns_none() -> None:
    assert parse_score(None) is None


def test_parse_score_empty_string_returns_none() -> None:
    assert parse_score("") is None


def test_parse_score_integer_string() -> None:
    assert parse_score("2") == 2


def test_parse_score_integer_value() -> None:
    assert parse_score(3) == 3


def test_parse_score_invalid_returns_none() -> None:
    assert parse_score("N/A") is None


# ---------------------------------------------------------------------------
# parse_status
# ---------------------------------------------------------------------------


def test_parse_status_empty_is_scheduled() -> None:
    assert parse_status("") == "scheduled"


def test_parse_status_match_finished() -> None:
    assert parse_status("Match Finished") == "completed"


def test_parse_status_in_progress() -> None:
    assert parse_status("In Progress") == "live"


def test_parse_status_live_variants() -> None:
    for raw in ("1H", "2H", "HT", "ET", "PEN"):
        assert parse_status(raw) == "live", f"Expected 'live' for {raw!r}"


def test_parse_status_after_penalties() -> None:
    assert parse_status("AP") == "completed"


def test_parse_status_after_extra_time() -> None:
    assert parse_status("AET") == "completed"


def test_parse_status_full_time() -> None:
    assert parse_status("FT") == "completed"


def test_parse_status_unknown_is_scheduled() -> None:
    assert parse_status("Postponed") == "scheduled"


# ---------------------------------------------------------------------------
# parse_round
# ---------------------------------------------------------------------------


def test_parse_round_unknown_defaults_to_group() -> None:
    assert parse_round("1") == "group"


def test_parse_round_round_of_32() -> None:
    assert parse_round("Round of 32") == "r32"


def test_parse_round_semi_final() -> None:
    assert parse_round("Semi Final") == "sf"
    assert parse_round("Semi-Final") == "sf"


def test_parse_round_final() -> None:
    assert parse_round("Final") == "final"


# ---------------------------------------------------------------------------
# parse_scheduled_at
# ---------------------------------------------------------------------------


def test_parse_scheduled_at_valid() -> None:
    dt = parse_scheduled_at("2026-06-11", "19:00:00")
    assert dt.year == 2026
    assert dt.month == 6
    assert dt.day == 11
    assert dt.hour == 19


def test_parse_scheduled_at_none_inputs_returns_fallback() -> None:
    dt = parse_scheduled_at(None, None)
    assert dt.year == 2026  # fallback uses "2026-01-01"


# ---------------------------------------------------------------------------
# compute_elo_update
# ---------------------------------------------------------------------------


def test_elo_update_winner_gains_rating() -> None:
    new_winner, new_loser = compute_elo_update(1500.0, 1500.0)
    assert new_winner > 1500.0
    assert new_loser < 1500.0


def test_elo_update_sum_is_conserved() -> None:
    new_winner, new_loser = compute_elo_update(1600.0, 1400.0)
    assert abs((new_winner + new_loser) - (1600.0 + 1400.0)) < 1e-9


def test_elo_update_underdog_gains_more() -> None:
    # Equal Elo — each side gains/loses the same amount (K/2 = 16)
    w_eq, l_eq = compute_elo_update(1500.0, 1500.0)
    assert abs(w_eq - 1516.0) < 0.01
    assert abs(l_eq - 1484.0) < 0.01

    # Weaker team wins — bigger gain than equal-match winner
    gain_equal = w_eq - 1500.0
    gain_upset = compute_elo_update(1400.0, 1600.0)[0] - 1400.0
    assert gain_upset > gain_equal


def test_elo_update_heavy_favourite_winning_gains_little() -> None:
    new_winner, _ = compute_elo_update(2000.0, 1000.0)
    assert new_winner - 2000.0 < 1.0  # very small gain when huge favourite wins


# ---------------------------------------------------------------------------
# handle_sync — upsert new match
# ---------------------------------------------------------------------------


@patch("api.handlers.sync_matches.fetch_live_and_recent_events")
@patch("api.handlers.sync_matches.get_container")
def test_sync_upserts_new_match(mock_gc: MagicMock, mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = [_SCHEDULED_EVENT]
    container = _mock_container(
        read_side_effect=[
            CosmosResourceNotFoundError(404, "not found"),  # match lookup
        ],
        query_result=[
            {"id": "MEX", "name": "Mexico"},
            {"id": "RSA", "name": "South Africa"},
        ],
    )
    mock_gc.return_value = container

    from api.handlers.sync_matches import handle_sync

    handle_sync(_timer())

    container.upsert_item.assert_called_once()
    doc = container.upsert_item.call_args.args[0]
    assert doc["id"] == "tsdb_2391728"
    assert doc["homeTeamId"] == "MEX"
    assert doc["awayTeamId"] == "RSA"
    assert doc["status"] == "scheduled"
    assert doc["homeScore"] is None


@patch("api.handlers.sync_matches.fetch_live_and_recent_events")
@patch("api.handlers.sync_matches.get_container")
def test_sync_upserted_new_match_writes_audit_log(
    mock_gc: MagicMock, mock_fetch: MagicMock
) -> None:
    mock_fetch.return_value = [_SCHEDULED_EVENT]
    container = _mock_container(
        read_side_effect=[CosmosResourceNotFoundError(404, "not found")],
        query_result=[{"id": "MEX", "name": "Mexico"}, {"id": "RSA", "name": "South Africa"}],
    )
    mock_gc.return_value = container

    from api.handlers.sync_matches import handle_sync

    handle_sync(_timer())

    container.create_item.assert_called_once()
    audit = container.create_item.call_args.args[0]
    assert audit["type"] == "audit"
    assert audit["action"] == "sync_upsert"
    assert audit["matchId"] == "tsdb_2391728"


# ---------------------------------------------------------------------------
# handle_sync — update existing match
# ---------------------------------------------------------------------------


@patch("api.handlers.sync_matches.fetch_live_and_recent_events")
@patch("api.handlers.sync_matches.get_container")
def test_sync_patches_existing_match_on_score_change(
    mock_gc: MagicMock, mock_fetch: MagicMock
) -> None:
    mock_fetch.return_value = [_COMPLETED_EVENT]
    container = _mock_container(
        query_result=[{"id": "MEX", "name": "Mexico"}, {"id": "RSA", "name": "South Africa"}],
    )
    container.read_item.side_effect = [
        _EXISTING_SCHEDULED_DOC,  # match lookup
    ]
    mock_gc.return_value = container

    from api.handlers.sync_matches import handle_sync

    handle_sync(_timer())

    container.patch_item.assert_called()
    patch_call = container.patch_item.call_args_list[0]
    assert patch_call.kwargs["item"] == "tsdb_2391728"
    assert patch_call.kwargs["partition_key"] == "match"
    ops = {op["path"]: op["value"] for op in patch_call.kwargs["patch_operations"]}
    assert ops["/status"] == "completed"
    assert ops["/homeScore"] == 2
    assert ops["/awayScore"] == 1
    assert ops["/winnerId"] == "MEX"


@patch("api.handlers.sync_matches.fetch_live_and_recent_events")
@patch("api.handlers.sync_matches.get_container")
def test_sync_skips_unchanged_match(mock_gc: MagicMock, mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = [_SCHEDULED_EVENT]
    already_scheduled = {**_EXISTING_SCHEDULED_DOC, "status": "scheduled"}
    container = _mock_container(
        query_result=[{"id": "MEX", "name": "Mexico"}, {"id": "RSA", "name": "South Africa"}],
    )
    container.read_item.return_value = already_scheduled
    mock_gc.return_value = container

    from api.handlers.sync_matches import handle_sync

    handle_sync(_timer())

    container.patch_item.assert_not_called()
    container.upsert_item.assert_not_called()
    container.create_item.assert_not_called()


# ---------------------------------------------------------------------------
# handle_sync — Elo update on completion
# ---------------------------------------------------------------------------


@patch("api.handlers.sync_matches.fetch_live_and_recent_events")
@patch("api.handlers.sync_matches.get_container")
def test_sync_triggers_elo_update_on_completion(mock_gc: MagicMock, mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = [_COMPLETED_EVENT]
    winner_doc = {"id": "MEX", "eloRating": 1600.0}
    loser_doc = {"id": "RSA", "eloRating": 1400.0}
    container = _mock_container(
        query_result=[{"id": "MEX", "name": "Mexico"}, {"id": "RSA", "name": "South Africa"}],
    )
    # read_item calls: match lookup, then winner team, then loser team
    container.read_item.side_effect = [_EXISTING_SCHEDULED_DOC, winner_doc, loser_doc]
    mock_gc.return_value = container

    from api.handlers.sync_matches import handle_sync

    handle_sync(_timer())

    # Two patch_item calls: winner Elo + loser Elo (plus the match patch = 3 total)
    patch_calls = container.patch_item.call_args_list
    elo_calls = [c for c in patch_calls if c.kwargs.get("partition_key") == "team"]
    assert len(elo_calls) == 2

    winner_call = next(c for c in elo_calls if c.kwargs["item"] == "MEX")
    loser_call = next(c for c in elo_calls if c.kwargs["item"] == "RSA")
    new_winner_elo = winner_call.kwargs["patch_operations"][0]["value"]
    new_loser_elo = loser_call.kwargs["patch_operations"][0]["value"]
    assert new_winner_elo > 1600.0
    assert new_loser_elo < 1400.0


@patch("api.handlers.sync_matches.fetch_live_and_recent_events")
@patch("api.handlers.sync_matches.get_container")
def test_sync_no_elo_update_for_draw(mock_gc: MagicMock, mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = [_DRAW_EVENT]
    container = _mock_container(
        query_result=[{"id": "MEX", "name": "Mexico"}, {"id": "RSA", "name": "South Africa"}],
    )
    container.read_item.return_value = _EXISTING_SCHEDULED_DOC
    mock_gc.return_value = container

    from api.handlers.sync_matches import handle_sync

    handle_sync(_timer())

    elo_calls = [
        c for c in container.patch_item.call_args_list if c.kwargs.get("partition_key") == "team"
    ]
    assert len(elo_calls) == 0  # no Elo update for draws


@patch("api.handlers.sync_matches.fetch_live_and_recent_events")
@patch("api.handlers.sync_matches.get_container")
def test_sync_no_elo_update_if_already_completed(mock_gc: MagicMock, mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = [_COMPLETED_EVENT]
    already_completed = {
        **_EXISTING_SCHEDULED_DOC,
        "status": "completed",
        "homeScore": 2,
        "awayScore": 1,
        "winnerId": "MEX",
    }
    container = _mock_container(
        query_result=[{"id": "MEX", "name": "Mexico"}, {"id": "RSA", "name": "South Africa"}],
    )
    container.read_item.return_value = already_completed
    mock_gc.return_value = container

    from api.handlers.sync_matches import handle_sync

    handle_sync(_timer())

    elo_calls = [
        c for c in container.patch_item.call_args_list if c.kwargs.get("partition_key") == "team"
    ]
    assert len(elo_calls) == 0


# ---------------------------------------------------------------------------
# handle_sync — idempotency
# ---------------------------------------------------------------------------


@patch("api.handlers.sync_matches.fetch_live_and_recent_events")
@patch("api.handlers.sync_matches.get_container")
def test_sync_idempotent_on_unchanged_data(mock_gc: MagicMock, mock_fetch: MagicMock) -> None:
    already_completed = {
        **_EXISTING_SCHEDULED_DOC,
        "status": "completed",
        "homeScore": 2,
        "awayScore": 1,
        "winnerId": "MEX",
    }
    mock_fetch.return_value = [_COMPLETED_EVENT]
    container = _mock_container(
        query_result=[{"id": "MEX", "name": "Mexico"}, {"id": "RSA", "name": "South Africa"}],
    )
    container.read_item.return_value = already_completed
    mock_gc.return_value = container

    from api.handlers.sync_matches import handle_sync

    handle_sync(_timer())
    handle_sync(_timer())

    container.patch_item.assert_not_called()
    container.upsert_item.assert_not_called()
    container.create_item.assert_not_called()


# ---------------------------------------------------------------------------
# handle_sync — skips unknown teams
# ---------------------------------------------------------------------------


@patch("api.handlers.sync_matches.fetch_live_and_recent_events")
@patch("api.handlers.sync_matches.get_container")
def test_sync_skips_event_with_unresolvable_teams(
    mock_gc: MagicMock, mock_fetch: MagicMock
) -> None:
    unknown_event = {**_SCHEDULED_EVENT, "strHomeTeam": "UnknownFC", "strAwayTeam": "MysteryXI"}
    mock_fetch.return_value = [unknown_event]
    container = _mock_container(
        read_side_effect=[CosmosResourceNotFoundError(404, "not found")],
        query_result=[{"id": "MEX", "name": "Mexico"}],
    )
    mock_gc.return_value = container

    from api.handlers.sync_matches import handle_sync

    handle_sync(_timer())

    container.upsert_item.assert_not_called()
    container.patch_item.assert_not_called()


# ---------------------------------------------------------------------------
# handle_sync — aborts gracefully when TheSportsDB returns nothing
# ---------------------------------------------------------------------------


@patch("api.handlers.sync_matches.fetch_season_events")
@patch("api.handlers.sync_matches.fetch_live_and_recent_events")
@patch("api.handlers.sync_matches.get_container")
def test_sync_aborts_when_no_events_returned(
    mock_gc: MagicMock, mock_live: MagicMock, mock_season: MagicMock
) -> None:
    mock_live.return_value = []
    mock_season.return_value = []
    container = MagicMock()
    mock_gc.return_value = container

    from api.handlers.sync_matches import handle_sync

    handle_sync(_timer())

    container.query_items.assert_not_called()
    container.upsert_item.assert_not_called()


# ---------------------------------------------------------------------------
# fetch_live_and_recent_events — season-year filter
# ---------------------------------------------------------------------------


def _make_mock_response(events: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"events": events}
    return resp


@patch("api.sync_matches.thesportsdb.httpx.get")
def test_fetch_filters_out_past_season_events(mock_get: MagicMock) -> None:
    past_event = {**_SCHEDULED_EVENT, "idEvent": "999", "dateEvent": "2022-12-18"}
    current_event = {**_SCHEDULED_EVENT, "idEvent": "2391728", "dateEvent": "2026-06-11"}
    mock_get.return_value = _make_mock_response([past_event, current_event])

    events = fetch_live_and_recent_events("4429", "3", season_year=2026)

    ids = [e["idEvent"] for e in events]
    assert "2391728" in ids
    assert "999" not in ids, "2022 event should be filtered out"


@patch("api.sync_matches.thesportsdb.httpx.get")
def test_fetch_keeps_events_with_no_date(mock_get: MagicMock) -> None:
    no_date_event = {**_SCHEDULED_EVENT, "idEvent": "555", "dateEvent": None}
    mock_get.return_value = _make_mock_response([no_date_event])

    events = fetch_live_and_recent_events("4429", "3", season_year=2026)

    assert any(e["idEvent"] == "555" for e in events), "Events without a date should pass through"


@patch("api.sync_matches.thesportsdb.httpx.get")
def test_fetch_deduplicates_across_endpoints(mock_get: MagicMock) -> None:
    event = {**_SCHEDULED_EVENT, "idEvent": "2391728", "dateEvent": "2026-06-11"}
    mock_get.return_value = _make_mock_response([event])

    events = fetch_live_and_recent_events("4429", "3", season_year=2026)

    assert len([e for e in events if e["idEvent"] == "2391728"]) == 1, "Duplicate ids should be deduped"
