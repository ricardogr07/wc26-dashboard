from datetime import UTC, datetime

import pytest

from api.models import Match, Participant, SimulationRun, Team


@pytest.fixture
def participant() -> Participant:
    return Participant(
        id="ricardo",
        display_name="Ricardo",
        team_ids=["MEX", "ARG", "GER", "NED", "SEN"],
    )


@pytest.fixture
def team() -> Team:
    return Team(id="MEX", name="Mexico", group="C", elo_rating=1680.0)


@pytest.fixture
def scheduled_match() -> Match:
    return Match(
        id="match_001",
        round="group",
        group="C",
        home_team_id="MEX",
        away_team_id="POL",
        scheduled_at=datetime(2026, 6, 15, 19, 0, 0, tzinfo=UTC),
        venue="SoFi Stadium",
        source="thesportsdb",
        last_updated=datetime(2026, 6, 9, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def completed_match() -> Match:
    return Match(
        id="match_001",
        round="group",
        group="C",
        home_team_id="MEX",
        away_team_id="POL",
        scheduled_at=datetime(2026, 6, 15, 19, 0, 0, tzinfo=UTC),
        venue="SoFi Stadium",
        home_score=2,
        away_score=1,
        winner_id="MEX",
        status="completed",
        source="thesportsdb",
        last_updated=datetime(2026, 6, 9, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def simulation_run() -> SimulationRun:
    return SimulationRun(
        id="sim_20260609_120000",
        run_at=datetime(2026, 6, 9, 12, 0, 0, tzinfo=UTC),
        matches_completed_at_run=12,
        n_runs=10000,
        win_probabilities={
            "ricardo": 0.32,
            "jibran": 0.25,
        },
    )
