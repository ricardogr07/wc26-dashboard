from __future__ import annotations

from api.simulation.bracket import elo_win_prob

_K = 32


def compute_elo_update(winner_elo: float, loser_elo: float) -> tuple[float, float]:
    """Return (new_winner_elo, new_loser_elo) after a decisive match result.

    Uses K=32 per the tournament configuration in plan.md.
    """
    p_win = elo_win_prob(winner_elo, loser_elo)
    new_winner = winner_elo + _K * (1 - p_win)
    new_loser = loser_elo + _K * (0 - (1 - p_win))
    return new_winner, new_loser
