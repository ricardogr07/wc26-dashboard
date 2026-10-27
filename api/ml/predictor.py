from __future__ import annotations

import logging
import os
from pathlib import Path

from api.ml.features import build_feature
from api.simulation.bracket import elo_win_prob

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_PATH = Path(__file__).parent.parent.parent / "shared" / "model" / "model.joblib"


def get_model_path() -> Path:
    env = os.environ.get("MODEL_PATH")
    return Path(env) if env else _DEFAULT_MODEL_PATH


class Predictor:
    """Wraps a trained sklearn model; callable as predict(home_elo, away_elo, is_knockout)."""

    def __init__(self, model: object) -> None:
        self._model = model

    def __call__(self, home_elo: float, away_elo: float, is_knockout: bool) -> float:
        features = [build_feature(home_elo, away_elo, is_knockout)]
        try:
            return float(self._model.predict_proba(features)[0][1])  # type: ignore[attr-defined]
        except Exception:
            logger.warning("Predictor inference failed; falling back to Elo", exc_info=True)
            return elo_win_prob(home_elo, away_elo)


def load_predictor() -> Predictor | None:
    """Load model.joblib from MODEL_PATH (or default). Returns None if absent or broken."""
    path = get_model_path()
    if not path.exists():
        logger.debug("No model at %s; using Elo only", path)
        return None
    try:
        import joblib  # type: ignore[import-untyped]

        model = joblib.load(path)
        logger.info("ML predictor loaded from %s", path)
        return Predictor(model)
    except Exception:
        logger.warning("Failed to load model from %s; using Elo only", path, exc_info=True)
        return None
