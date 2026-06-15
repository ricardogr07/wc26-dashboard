from __future__ import annotations


def build_feature(home_elo: float, away_elo: float, is_knockout: bool) -> list[float]:
    """Three-element pre-match feature vector (no leakage).

    [elo_diff, is_knockout, is_neutral]
    is_neutral is always 1.0 for WC2026 (all matches at neutral venues).
    """
    return [home_elo - away_elo, float(is_knockout), 1.0]
