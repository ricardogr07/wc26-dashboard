from datetime import UTC, datetime

import pytest

from api.models import Match, Participant, Team
from api.models.match import MatchRound, MatchStatus
from api.scoring import GROUP_QUALIFICATION_POINTS, ROUND_WIN_POINTS, compute_scores

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)


def _match(
    id: str,
    round: MatchRound,
    home: str,
    away: str,
    *,
    status: MatchStatus = "scheduled",
    winner_id: str | None = None,
    home_score: int | None = None,
    away_score: int | None = None,
    group: str | None = None,
) -> Match:
    return Match(
        id=id,
        round=round,
        group=group,
        home_team_id=home,
        away_team_id=away,
        scheduled_at=_NOW,
        status=status,
        winner_id=winner_id,
        home_score=home_score,
        away_score=away_score,
        source="test",
        last_updated=_NOW,
    )


def _participant(id: str, *team_ids: str) -> Participant:
    return Participant(id=id, display_name=id.capitalize(), team_ids=list(team_ids))


def _team(id: str) -> Team:
    return Team(id=id, name=id, group="A", elo_rating=1600.0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def two_participants() -> list[Participant]:
    return [
        _participant("alice", "MEX", "ARG"),
        _participant("bob", "GER", "FRA"),
    ]


@pytest.fixture
def teams() -> list[Team]:
    return [_team(t) for t in ("MEX", "ARG", "GER", "FRA", "POL", "USA")]


# ---------------------------------------------------------------------------
# Zero-state tests
# ---------------------------------------------------------------------------


def test_all_zero_no_matches(two_participants: list[Participant], teams: list[Team]) -> None:
    scores = compute_scores([], two_participants, teams)
    assert scores == {"alice": 0, "bob": 0}


def test_all_zero_group_matches_only(
    two_participants: list[Participant], teams: list[Team]
) -> None:
    matches = [
        _match("g1", "group", "MEX", "POL", status="completed", winner_id="MEX", group="C"),
        _match("g2", "group", "ARG", "USA", status="completed", winner_id="ARG", group="D"),
    ]
    scores = compute_scores(matches, two_participants, teams)
    assert scores == {"alice": 0, "bob": 0}


# ---------------------------------------------------------------------------
# Group qualification
# ---------------------------------------------------------------------------


def test_group_qualification(two_participants: list[Participant], teams: list[Team]) -> None:
    matches = [_match("r1", "r32", "MEX", "USA")]
    scores = compute_scores(matches, two_participants, teams)
    assert scores["alice"] == GROUP_QUALIFICATION_POINTS
    assert scores["bob"] == 0


def test_group_qual_both_teams(two_participants: list[Participant], teams: list[Team]) -> None:
    matches = [_match("r1", "r32", "MEX", "GER")]
    scores = compute_scores(matches, two_participants, teams)
    assert scores["alice"] == GROUP_QUALIFICATION_POINTS
    assert scores["bob"] == GROUP_QUALIFICATION_POINTS


def test_group_qual_not_double_counted(
    two_participants: list[Participant], teams: list[Team]
) -> None:
    # Same team appears as home in two r32 matches (data anomaly guard)
    matches = [
        _match("r1", "r32", "MEX", "USA"),
        _match("r2", "r32", "MEX", "POL"),
    ]
    scores = compute_scores(matches, two_participants, teams)
    assert scores["alice"] == GROUP_QUALIFICATION_POINTS


# ---------------------------------------------------------------------------
# Knockout win milestones
# ---------------------------------------------------------------------------


def _champion_path(team: str, opponent: str) -> list[Match]:
    """Full set of matches for a team that wins every knockout round."""
    return [
        _match("r32m", "r32", team, opponent),
        _match(
            "r32w",
            "r32",
            team,
            opponent,
            status="completed",
            winner_id=team,
            home_score=2,
            away_score=1,
        ),
        _match("r16m", "r16", team, opponent),
        _match(
            "r16w",
            "r16",
            team,
            opponent,
            status="completed",
            winner_id=team,
            home_score=1,
            away_score=0,
        ),
        _match("qfm", "qf", team, opponent),
        _match(
            "qfw",
            "qf",
            team,
            opponent,
            status="completed",
            winner_id=team,
            home_score=3,
            away_score=2,
        ),
        _match("sfm", "sf", team, opponent),
        _match(
            "sfw",
            "sf",
            team,
            opponent,
            status="completed",
            winner_id=team,
            home_score=2,
            away_score=0,
        ),
        _match("fin", "final", team, opponent),
        _match(
            "finw",
            "final",
            team,
            opponent,
            status="completed",
            winner_id=team,
            home_score=1,
            away_score=0,
        ),
    ]


def test_r32_win(two_participants: list[Participant], teams: list[Team]) -> None:
    matches = [
        _match("r32m", "r32", "MEX", "USA"),
        _match(
            "r32w",
            "r32",
            "MEX",
            "USA",
            status="completed",
            winner_id="MEX",
            home_score=2,
            away_score=1,
        ),
    ]
    scores = compute_scores(matches, two_participants, teams)
    assert scores["alice"] == GROUP_QUALIFICATION_POINTS + ROUND_WIN_POINTS["r32"]


def test_r16_win(two_participants: list[Participant], teams: list[Team]) -> None:
    matches = [
        _match("r32m", "r32", "MEX", "USA"),
        _match(
            "r32w",
            "r32",
            "MEX",
            "USA",
            status="completed",
            winner_id="MEX",
            home_score=2,
            away_score=1,
        ),
        _match("r16m", "r16", "MEX", "POL"),
        _match(
            "r16w",
            "r16",
            "MEX",
            "POL",
            status="completed",
            winner_id="MEX",
            home_score=1,
            away_score=0,
        ),
    ]
    scores = compute_scores(matches, two_participants, teams)
    expected = GROUP_QUALIFICATION_POINTS + ROUND_WIN_POINTS["r32"] + ROUND_WIN_POINTS["r16"]
    assert scores["alice"] == expected


def test_qf_win(two_participants: list[Participant], teams: list[Team]) -> None:
    matches = [
        _match("r32m", "r32", "MEX", "USA"),
        _match(
            "r32w",
            "r32",
            "MEX",
            "USA",
            status="completed",
            winner_id="MEX",
            home_score=1,
            away_score=0,
        ),
        _match("r16m", "r16", "MEX", "POL"),
        _match(
            "r16w",
            "r16",
            "MEX",
            "POL",
            status="completed",
            winner_id="MEX",
            home_score=1,
            away_score=0,
        ),
        _match("qfm", "qf", "MEX", "USA"),
        _match(
            "qfw",
            "qf",
            "MEX",
            "USA",
            status="completed",
            winner_id="MEX",
            home_score=2,
            away_score=1,
        ),
    ]
    scores = compute_scores(matches, two_participants, teams)
    expected = (
        GROUP_QUALIFICATION_POINTS
        + ROUND_WIN_POINTS["r32"]
        + ROUND_WIN_POINTS["r16"]
        + ROUND_WIN_POINTS["qf"]
    )
    assert scores["alice"] == expected
    assert scores["bob"] == 0


def test_sf_win(two_participants: list[Participant], teams: list[Team]) -> None:
    matches = [
        _match("r32m", "r32", "MEX", "USA"),
        _match(
            "r32w",
            "r32",
            "MEX",
            "USA",
            status="completed",
            winner_id="MEX",
            home_score=1,
            away_score=0,
        ),
        _match(
            "r16w",
            "r16",
            "MEX",
            "POL",
            status="completed",
            winner_id="MEX",
            home_score=1,
            away_score=0,
        ),
        _match(
            "qfw",
            "qf",
            "MEX",
            "USA",
            status="completed",
            winner_id="MEX",
            home_score=1,
            away_score=0,
        ),
        _match("sfm", "sf", "MEX", "FRA"),
        _match(
            "sfw",
            "sf",
            "MEX",
            "FRA",
            status="completed",
            winner_id="MEX",
            home_score=1,
            away_score=0,
        ),
    ]
    scores = compute_scores(matches, two_participants, teams)
    expected = (
        GROUP_QUALIFICATION_POINTS
        + ROUND_WIN_POINTS["r32"]
        + ROUND_WIN_POINTS["r16"]
        + ROUND_WIN_POINTS["qf"]
        + ROUND_WIN_POINTS["sf"]
    )
    assert scores["alice"] == expected


def test_champion_earns_32_points(two_participants: list[Participant], teams: list[Team]) -> None:
    matches = _champion_path("MEX", "USA")
    scores = compute_scores(matches, two_participants, teams)
    assert scores["alice"] == 32  # 1+2+3+5+8+13


# ---------------------------------------------------------------------------
# Accumulation
# ---------------------------------------------------------------------------


def test_accumulation_multi_team() -> None:
    participants = [_participant("alice", "MEX", "ARG"), _participant("bob", "GER")]
    teams = [_team(t) for t in ("MEX", "ARG", "GER", "USA")]
    matches = [
        _match("r1", "r32", "MEX", "USA"),
        _match(
            "r1w",
            "r32",
            "MEX",
            "USA",
            status="completed",
            winner_id="MEX",
            home_score=1,
            away_score=0,
        ),
        _match("r2", "r32", "ARG", "GER"),
        _match(
            "r2w",
            "r32",
            "ARG",
            "GER",
            status="completed",
            winner_id="ARG",
            home_score=2,
            away_score=1,
        ),
    ]
    scores = compute_scores(matches, participants, teams)
    # alice: MEX qualifies(1) + MEX r32 win(2) + ARG qualifies(1) + ARG r32 win(2) = 6
    assert scores["alice"] == 6
    # bob: GER qualifies(1) + GER loses r32 = 1
    assert scores["bob"] == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_unowned_team_ignored(two_participants: list[Participant], teams: list[Team]) -> None:
    # POL is not owned by anyone
    matches = [
        _match("r1", "r32", "POL", "USA"),
        _match(
            "r1w",
            "r32",
            "POL",
            "USA",
            status="completed",
            winner_id="POL",
            home_score=1,
            away_score=0,
        ),
    ]
    scores = compute_scores(matches, two_participants, teams)
    assert scores == {"alice": 0, "bob": 0}


def test_draw_no_winner(two_participants: list[Participant], teams: list[Team]) -> None:
    # Completed r32 match with no winner (data anomaly; knockouts always have a winner,
    # but the function must not crash and must not award points)
    matches = [
        _match("r1", "r32", "MEX", "GER"),
        _match(
            "r1c",
            "r32",
            "MEX",
            "GER",
            status="completed",
            winner_id=None,
            home_score=1,
            away_score=1,
        ),
    ]
    scores = compute_scores(matches, two_participants, teams)
    # Both teams qualified (1 pt each owner), no win points awarded
    assert scores["alice"] == GROUP_QUALIFICATION_POINTS
    assert scores["bob"] == GROUP_QUALIFICATION_POINTS


def test_mid_tournament(two_participants: list[Participant], teams: list[Team]) -> None:
    matches = [
        # r32 done
        _match("r1", "r32", "MEX", "USA"),
        _match(
            "r1w",
            "r32",
            "MEX",
            "USA",
            status="completed",
            winner_id="MEX",
            home_score=2,
            away_score=0,
        ),
        _match("r2", "r32", "GER", "FRA"),
        _match(
            "r2w",
            "r32",
            "GER",
            "FRA",
            status="completed",
            winner_id="GER",
            home_score=1,
            away_score=0,
        ),
        # r16 scheduled but not completed
        _match("r16", "r16", "MEX", "GER"),
    ]
    scores = compute_scores(matches, two_participants, teams)
    # alice: MEX qualifies(1) + MEX r32 win(2) = 3
    assert scores["alice"] == 3
    # bob: GER qualifies(1) + GER r32 win(2), FRA qualifies(1) = 4
    assert scores["bob"] == 4


def test_tie_scores() -> None:
    participants = [_participant("alice", "MEX"), _participant("bob", "ARG")]
    teams = [_team(t) for t in ("MEX", "ARG", "USA", "BRA")]
    matches = [
        _match("r1", "r32", "MEX", "USA"),
        _match("r2", "r32", "ARG", "BRA"),
    ]
    scores = compute_scores(matches, participants, teams)
    assert scores["alice"] == scores["bob"] == GROUP_QUALIFICATION_POINTS


# ---------------------------------------------------------------------------
# Purity contract
# ---------------------------------------------------------------------------


def test_no_cloud_imports() -> None:
    import importlib
    import importlib.util

    spec = importlib.util.spec_from_file_location("api.scoring", "api/scoring.py")
    assert spec is not None
    source = spec.origin
    assert source is not None
    with open(source) as f:
        content = f.read()

    for forbidden in ("azure", "cosmos", "httpx"):
        assert forbidden not in content, f"api/scoring.py must not import '{forbidden}'"
