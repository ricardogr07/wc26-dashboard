"""Tests for the Monte Carlo simulation engine."""

from __future__ import annotations

import time
from typing import Any

import pytest

from api.models import Match, Participant, Team  # noqa: F401
from api.seed import load_fixtures, load_participants, load_teams
from api.simulation.engine import run_simulation

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_teams() -> list[Team]:
    return load_teams()


@pytest.fixture(scope="module")
def real_participants() -> list[Participant]:
    return load_participants()


@pytest.fixture(scope="module")
def real_fixtures() -> list[Match]:
    return load_fixtures()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_determinism(
    real_fixtures: list[Match],
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    r1 = run_simulation(real_fixtures, real_participants, real_teams, n_runs=200, seed=42)
    r2 = run_simulation(real_fixtures, real_participants, real_teams, n_runs=200, seed=42)
    assert r1.win_probabilities == r2.win_probabilities


def test_different_seeds_produce_different_results(
    real_fixtures: list[Match],
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    r1 = run_simulation(real_fixtures, real_participants, real_teams, n_runs=500, seed=1)
    r2 = run_simulation(real_fixtures, real_participants, real_teams, n_runs=500, seed=2)
    assert r1.win_probabilities != r2.win_probabilities


# ---------------------------------------------------------------------------
# Probability integrity
# ---------------------------------------------------------------------------


def test_win_probabilities_bounded(
    real_fixtures: list[Match],
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    # Probabilities sum to ≤ 1.0; they may be < 1.0 when an unowned team wins.
    # Each participant owns 5 of 48 teams, so ~23 teams can win without crediting anyone.
    result = run_simulation(real_fixtures, real_participants, real_teams, n_runs=1_000, seed=0)
    total = sum(result.win_probabilities.values())
    assert 0.0 < total <= 1.0 + 1e-9, f"Win probabilities out of range: {total}"
    for pid, prob in result.win_probabilities.items():
        assert 0.0 <= prob <= 1.0, f"Out-of-range probability for {pid}: {prob}"


def test_all_participants_have_win_probabilities(
    real_fixtures: list[Match],
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    result = run_simulation(real_fixtures, real_participants, real_teams, n_runs=100, seed=0)
    expected_ids = {p.id for p in real_participants}
    assert set(result.win_probabilities.keys()) == expected_ids


def test_win_probabilities_non_negative(
    real_fixtures: list[Match],
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    result = run_simulation(real_fixtures, real_participants, real_teams, n_runs=200, seed=3)
    for pid, prob in result.win_probabilities.items():
        assert prob >= 0.0, f"Negative win probability for {pid}"


# ---------------------------------------------------------------------------
# Real-bracket mode (post-group stage)
# ---------------------------------------------------------------------------


def _bracket_matches() -> list[Match]:
    """Full knockout docs: R32 completed (odd team wins), later rounds pending."""
    common: dict[str, Any] = {
        "scheduled_at": "2026-07-01T00:00:00Z",
        "source": "test",
        "last_updated": "2026-07-01T00:00:00Z",
    }
    matches = [
        Match(
            id=f"r32_{73 + i}",
            round="r32",
            home_team_id=f"t{2 * i + 1}",
            away_team_id=f"t{2 * i + 2}",
            status="completed",
            winner_id=f"t{2 * i + 1}",
            **common,
        )
        for i in range(16)
    ]
    for rnd, first, prev_rnd, prev_first, n in (
        ("r16", 89, "R32", 73, 8),
        ("qf", 97, "R16", 89, 4),
        ("sf", 101, "QF", 97, 2),
        ("final", 104, "SF", 101, 1),
    ):
        matches += [
            Match(
                id=f"{rnd}_{first + i}",
                round=rnd,  # type: ignore[arg-type]
                home_team_id=f"TBD_{prev_rnd}_{prev_rnd.lower()}_{prev_first + 2 * i}",
                away_team_id=f"TBD_{prev_rnd}_{prev_rnd.lower()}_{prev_first + 2 * i + 1}",
                **common,
            )
            for i in range(n)
        ]
    return matches


def test_eliminated_participant_has_zero_probability() -> None:
    teams = [Team(id=f"t{i}", name=f"T{i}", group="A", elo_rating=1500.0) for i in range(1, 33)]
    participants = [
        Participant(id="p_alive", display_name="Alive", team_ids=["t1"]),
        Participant(id="p_out", display_name="Out", team_ids=["t2"]),  # t2 lost its R32 match
    ]
    result = run_simulation(_bracket_matches(), participants, teams, n_runs=500, seed=7)
    assert result.win_probabilities["p_out"] == 0.0
    assert result.win_probabilities["p_alive"] > 0.0
    assert all(result.team_win_probabilities.get(f"t{i}", 0.0) == 0.0 for i in range(2, 33, 2))


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_n_runs_recorded(
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    result = run_simulation([], real_participants, real_teams, n_runs=250, seed=0)
    assert result.n_runs == 250


def test_id_is_simulationrun_latest(
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    result = run_simulation([], real_participants, real_teams, n_runs=10, seed=0)
    assert result.id == "simulationRun_latest"


def test_matches_completed_count_no_matches(
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    result = run_simulation([], real_participants, real_teams, n_runs=10, seed=0)
    assert result.matches_completed_at_run == 0


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_performance_10k_runs(
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    start = time.monotonic()
    run_simulation([], real_participants, real_teams, n_runs=10_000, seed=0)
    elapsed = time.monotonic() - start
    assert elapsed < 10.0, f"10k runs took {elapsed:.2f}s; must be < 10s"


# ---------------------------------------------------------------------------
# Purity contract
# ---------------------------------------------------------------------------


def test_no_cloud_imports() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "api.simulation.engine", "api/simulation/engine.py"
    )
    assert spec is not None
    source = spec.origin
    assert source is not None
    with open(source) as f:
        content = f.read()

    for forbidden in ("azure", "cosmos", "httpx"):
        assert forbidden not in content, f"api/simulation/engine.py must not import '{forbidden}'"
