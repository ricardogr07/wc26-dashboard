from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from api.ml.features import build_feature
from api.models import Match, Team
from api.simulation.bracket import elo_win_prob

logger = logging.getLogger(__name__)

_MIN_SAMPLES = 10


@dataclass
class TrainingResult:
    n_samples: int
    log_loss: float
    brier_score: float
    elo_log_loss: float
    elo_brier_score: float
    model_beats_elo: bool


def train_and_save(matches: list[Match], teams: list[Team], model_path: Path) -> TrainingResult:
    """Train LogisticRegression on completed matches, write model.joblib, return metrics.

    Raises ValueError if fewer than _MIN_SAMPLES completed matches exist.
    Raises RuntimeError if scikit-learn / joblib are not installed.
    """
    try:
        import joblib  # type: ignore[import-untyped]
        from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
        from sklearn.metrics import brier_score_loss, log_loss  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("scikit-learn and joblib are required for ML training") from exc

    team_elo: dict[str, float] = {t.id: t.elo_rating for t in teams}

    x_train: list[list[float]] = []
    y: list[int] = []
    elo_proba: list[float] = []

    for m in matches:
        if m.status != "completed" or m.winner_id is None:
            continue
        home_elo = team_elo.get(m.home_team_id, 1500.0)
        away_elo = team_elo.get(m.away_team_id, 1500.0)
        is_knockout = m.round != "group"
        x_train.append(build_feature(home_elo, away_elo, is_knockout))
        y.append(1 if m.winner_id == m.home_team_id else 0)
        elo_proba.append(elo_win_prob(home_elo, away_elo))

    n = len(x_train)
    if n < _MIN_SAMPLES:
        raise ValueError(f"Not enough completed matches to train ({n} < {_MIN_SAMPLES})")

    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(x_train, y)

    proba = model.predict_proba(x_train)[:, 1]  # type: ignore[bad-argument-type]
    ml_ll = float(log_loss(y, proba))
    ml_bs = float(brier_score_loss(y, proba))
    elo_ll = float(log_loss(y, elo_proba))
    elo_bs = float(brier_score_loss(y, elo_proba))

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    logger.info(
        "Model saved to %s (n=%d, log_loss=%.4f vs elo_log_loss=%.4f)", model_path, n, ml_ll, elo_ll
    )

    return TrainingResult(
        n_samples=n,
        log_loss=ml_ll,
        brier_score=ml_bs,
        elo_log_loss=elo_ll,
        elo_brier_score=elo_bs,
        model_beats_elo=ml_ll < elo_ll,
    )
