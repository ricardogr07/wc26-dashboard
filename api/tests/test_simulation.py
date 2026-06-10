"""Tests for the Monte Carlo simulation engine."""

from __future__ import annotations

import time

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
    assert r1.probabilities == r2.probabilities


def test_different_seeds_produce_different_results(
    real_fixtures: list[Match],
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    r1 = run_simulation(real_fixtures, real_participants, real_teams, n_runs=500, seed=1)
    r2 = run_simulation(real_fixtures, real_participants, real_teams, n_runs=500, seed=2)
    assert r1.probabilities != r2.probabilities


# ---------------------------------------------------------------------------
# Probability integrity
# ---------------------------------------------------------------------------


def test_probabilities_sum_to_one(
    real_fixtures: list[Match],
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    result = run_simulation(real_fixtures, real_participants, real_teams, n_runs=1_000, seed=0)
    for pid, dist in result.probabilities.items():
        total = sum(dist.values())
        assert abs(total - 1.0) < 1e-9, f"Probabilities for {pid} sum to {total}"


def test_all_participants_have_probabilities(
    real_fixtures: list[Match],
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    result = run_simulation(real_fixtures, real_participants, real_teams, n_runs=100, seed=0)
    expected_ids = {p.id for p in real_participants}
    assert set(result.probabilities.keys()) == expected_ids


def test_all_ranks_covered(
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    result = run_simulation([], real_participants, real_teams, n_runs=500, seed=7)
    n = len(real_participants)
    expected_keys = {f"rank_{r}" for r in range(1, n + 1)}
    for pid, dist in result.probabilities.items():
        assert set(dist.keys()) == expected_keys, f"{pid} missing rank keys"


def test_probabilities_non_negative(
    real_fixtures: list[Match],
    real_participants: list[Participant],
    real_teams: list[Team],
) -> None:
    result = run_simulation(real_fixtures, real_participants, real_teams, n_runs=200, seed=3)
    for pid, dist in result.probabilities.items():
        for rank, prob in dist.items():
            assert prob >= 0.0, f"Negative probability for {pid} {rank}"


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
    assert elapsed < 3.0, f"10k runs took {elapsed:.2f}s — must be < 3s"


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
