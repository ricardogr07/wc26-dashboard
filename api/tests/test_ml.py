from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from api.ml.features import build_feature
from api.ml.predictor import Predictor
from api.models import Match, Participant, Team
from api.simulation.engine import run_simulation

# ── Helpers ──────────────────────────────────────────────────────────────────


class _ConstantModel:
    """Stub sklearn model that always predicts a fixed P(home wins)."""

    def __init__(self, p: float) -> None:
        self._p = p

    def predict_proba(self, x: list) -> list[list[float]]:
        return [[1 - self._p, self._p]] * len(x)


def _make_teams() -> list[Team]:
    return [
        Team(id="HOME", name="Home FC", group="A", elo_rating=1700.0),
        Team(id="AWAY", name="Away FC", group="A", elo_rating=1500.0),
    ]


def _make_match(i: int, winner: str = "HOME") -> Match:
    return Match(
        id=f"match_{i:03d}",
        round="group",
        group="A",
        home_team_id="HOME",
        away_team_id="AWAY",
        scheduled_at=datetime(2026, 6, 15, tzinfo=UTC),
        home_score=1 if winner == "HOME" else 0,
        away_score=0 if winner == "HOME" else 1,
        winner_id=winner,
        status="completed",
        source="test",
        last_updated=datetime(2026, 6, 15, tzinfo=UTC),
    )


# ── Feature extraction ───────────────────────────────────────────────────────


def test_build_feature_returns_three_elements() -> None:
    assert len(build_feature(1800.0, 1500.0, is_knockout=False)) == 3


def test_build_feature_elo_diff() -> None:
    feat = build_feature(1800.0, 1500.0, is_knockout=False)
    assert feat[0] == pytest.approx(300.0)


def test_build_feature_is_knockout_flag() -> None:
    assert build_feature(1500.0, 1500.0, is_knockout=True)[1] == 1.0
    assert build_feature(1500.0, 1500.0, is_knockout=False)[1] == 0.0


def test_build_feature_is_neutral_always_one() -> None:
    assert build_feature(1500.0, 1500.0, is_knockout=False)[2] == 1.0


# ── Predictor ────────────────────────────────────────────────────────────────


def test_predictor_returns_model_probability() -> None:
    pred = Predictor(_ConstantModel(0.7))
    assert pred(1800.0, 1500.0, is_knockout=False) == pytest.approx(0.7)


def test_predictor_probability_in_bounds() -> None:
    pred = Predictor(_ConstantModel(0.6))
    p = pred(1500.0, 1500.0, is_knockout=True)
    assert 0.0 <= p <= 1.0


def test_predictor_falls_back_to_elo_on_error() -> None:
    class _BrokenModel:
        def predict_proba(self, x: list) -> None:
            raise RuntimeError("boom")

    pred = Predictor(_BrokenModel())
    # Should not raise — falls back to Elo
    p = pred(1700.0, 1500.0, is_knockout=True)
    assert 0.0 < p < 1.0


# ── Trainer (skipped when scikit-learn not installed) ────────────────────────

sklearn = pytest.importorskip("sklearn", reason="scikit-learn not installed")

from api.ml.trainer import _MIN_SAMPLES, train_and_save  # noqa: E402


def test_trainer_raises_on_too_few_samples(tmp_path: Path) -> None:
    matches = [_make_match(i) for i in range(_MIN_SAMPLES - 1)]
    with pytest.raises(ValueError, match="Not enough"):
        train_and_save(matches, _make_teams(), tmp_path / "model.joblib")


def test_trainer_writes_model_file(tmp_path: Path) -> None:
    matches = [_make_match(i, winner="HOME" if i % 3 != 0 else "AWAY") for i in range(20)]
    train_and_save(matches, _make_teams(), tmp_path / "model.joblib")
    assert (tmp_path / "model.joblib").exists()


def test_training_result_metrics(tmp_path: Path) -> None:
    matches = [_make_match(i, winner="HOME" if i % 3 != 0 else "AWAY") for i in range(20)]
    result = train_and_save(matches, _make_teams(), tmp_path / "model.joblib")
    assert result.n_samples == 20
    assert result.log_loss > 0.0
    assert 0.0 <= result.brier_score <= 1.0
    assert isinstance(result.model_beats_elo, bool)


def test_trainer_creates_parent_dirs(tmp_path: Path) -> None:
    dest = tmp_path / "nested" / "dir" / "model.joblib"
    matches = [_make_match(i, winner="HOME" if i % 3 != 0 else "AWAY") for i in range(20)]
    train_and_save(matches, _make_teams(), dest)
    assert dest.exists()


def test_trained_predictor_gives_valid_probability(tmp_path: Path) -> None:
    matches = [_make_match(i, winner="HOME" if i % 3 != 0 else "AWAY") for i in range(20)]
    model_path = tmp_path / "model.joblib"
    train_and_save(matches, _make_teams(), model_path)

    import joblib

    model = joblib.load(model_path)
    pred = Predictor(model)
    p = pred(1700.0, 1500.0, is_knockout=False)
    assert 0.0 <= p <= 1.0


# ── Engine integration ───────────────────────────────────────────────────────


def test_simulation_with_predictor_produces_valid_output() -> None:
    pred = Predictor(_ConstantModel(0.6))
    participants = [
        Participant(id="p1", display_name="P1", team_ids=["HOME"]),
        Participant(id="p2", display_name="P2", team_ids=["AWAY"]),
    ]
    result = run_simulation([], participants, _make_teams(), n_runs=200, seed=1, predict=pred)
    assert set(result.win_probabilities) == {"p1", "p2"}
    assert sum(result.win_probabilities.values()) <= 1.0 + 1e-9


def test_simulation_predict_none_matches_default() -> None:
    """predict=None must give identical output to omitting the parameter."""
    participants = [
        Participant(id="p1", display_name="P1", team_ids=["HOME"]),
        Participant(id="p2", display_name="P2", team_ids=["AWAY"]),
    ]
    teams = _make_teams()
    r1 = run_simulation([], participants, teams, n_runs=500, seed=99, predict=None)
    r2 = run_simulation([], participants, teams, n_runs=500, seed=99)
    assert r1.win_probabilities == r2.win_probabilities
