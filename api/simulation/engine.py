"""Monte Carlo simulation engine for WC2026.

Pure function — no I/O, no Azure dependencies.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import UTC, datetime

from api.models import Match, Participant, Team
from api.models.simulation_run import SimulationRun
from api.scoring import GROUP_QUALIFICATION_POINTS, ROUND_WIN_POINTS
from api.simulation.bracket import (
    QF_BRACKET,
    R16_BRACKET,
    R32_SLOTS,
    SF_BRACKET,
    elo_win_prob,
)

_DRAW_RATE = 0.25


def _pick_winner(home: str, away: str, home_elo: float, away_elo: float, rng: random.Random) -> str:
    p = elo_win_prob(home_elo, away_elo)
    return home if rng.random() < p else away


def _simulate_group(
    teams: list[str],
    team_elo: dict[str, float],
    fixed_results: list[tuple[str, str, str | None]],
    pending_pairs: list[tuple[str, str]],
    rng: random.Random,
) -> list[str]:
    """Return teams ranked [1st, 2nd, 3rd, 4th] for a single group."""
    pts: dict[str, int] = dict.fromkeys(teams, 0)
    gd: dict[str, int] = dict.fromkeys(teams, 0)

    def _apply(home: str, away: str, winner: str | None) -> None:
        if winner == home:
            pts[home] += 3
            margin = rng.randint(1, 3)
            gd[home] += margin
            gd[away] -= margin
        elif winner == away:
            pts[away] += 3
            margin = rng.randint(1, 3)
            gd[away] += margin
            gd[home] -= margin
        else:  # draw
            pts[home] += 1
            pts[away] += 1

    for home, away, winner in fixed_results:
        _apply(home, away, winner)

    for home, away in pending_pairs:
        r = rng.random()
        home_p = elo_win_prob(team_elo.get(home, 1500.0), team_elo.get(away, 1500.0))
        if r < home_p * (1 - _DRAW_RATE):
            winner = home
        elif r < home_p * (1 - _DRAW_RATE) + _DRAW_RATE:
            winner = None  # draw
        else:
            winner = away
        _apply(home, away, winner)

    return sorted(teams, key=lambda t: (pts[t], gd[t], rng.random()), reverse=True)


def _sim_round(
    matchups: list[tuple[str, str]],
    round_name: str,
    scores: dict[str, int],
    team_owner: dict[str, str],
    team_elo: dict[str, float],
    completed_knockout: dict[tuple[str, str], str],
    rng: random.Random,
) -> list[str]:
    winners = []
    for home, away in matchups:
        key = (home, away)
        if key in completed_knockout and completed_knockout[key] in (home, away):
            w = completed_knockout[key]
        else:
            w = _pick_winner(
                home, away, team_elo.get(home, 1500.0), team_elo.get(away, 1500.0), rng
            )
        if w in team_owner:
            scores[team_owner[w]] += ROUND_WIN_POINTS[round_name]
        winners.append(w)
    return winners


def run_simulation(
    matches: list[Match],
    participants: list[Participant],
    teams: list[Team],
    n_runs: int = 10_000,
    seed: int | None = None,
) -> SimulationRun:
    # ------------------------------------------------------------------
    # One-time setup
    # ------------------------------------------------------------------
    rng = random.Random(seed)

    team_elo: dict[str, float] = {t.id: t.elo_rating for t in teams}
    team_group: dict[str, str] = {t.id: t.group for t in teams}
    team_owner: dict[str, str] = {tid: p.id for p in participants for tid in p.team_ids}
    participant_ids = [p.id for p in participants]

    # Build group → teams mapping from team data
    group_teams: dict[str, list[str]] = defaultdict(list)
    for t in teams:
        group_teams[t.group].append(t.id)

    # Partition group-stage matches
    # fixed: (home, away, winner_id | None)
    fixed_by_group: dict[str, list[tuple[str, str, str | None]]] = defaultdict(list)
    pending_by_group: dict[str, list[tuple[str, str]]] = defaultdict(list)

    # Knockout results already known (r32+)
    completed_knockout: dict[tuple[str, str], str] = {}  # (home, away) → winner_id

    completed_match_count = 0

    for m in matches:
        if m.round == "group":
            if m.status == "completed":
                completed_match_count += 1
                grp = m.group or team_group.get(m.home_team_id, "?")
                fixed_by_group[grp].append((m.home_team_id, m.away_team_id, m.winner_id))
            else:
                grp = m.group or team_group.get(m.home_team_id, "?")
                pending_by_group[grp].append((m.home_team_id, m.away_team_id))
        elif m.round in ROUND_WIN_POINTS and m.status == "completed" and m.winner_id:
            completed_match_count += 1
            completed_knockout[(m.home_team_id, m.away_team_id)] = m.winner_id

    # Pre-compute Elo win probabilities for pending group matches (constant per run)
    pending_group_probs: dict[str, list[tuple[str, str, float]]] = {}
    for grp, pairs in pending_by_group.items():
        pending_group_probs[grp] = [
            (h, a, elo_win_prob(team_elo.get(h, 1500.0), team_elo.get(a, 1500.0))) for h, a in pairs
        ]

    # ------------------------------------------------------------------
    # Aggregate counters
    # ------------------------------------------------------------------
    rank_counts: dict[str, dict[int, int]] = {p.id: defaultdict(int) for p in participants}

    # ------------------------------------------------------------------
    # Simulation loop
    # ------------------------------------------------------------------
    for _ in range(n_runs):
        scores: dict[str, int] = dict.fromkeys(participant_ids, 0)

        # ---- Group stage ----
        group_standings: dict[str, list[str]] = {}  # group → [1st,2nd,3rd,4th]

        for grp, g_teams in group_teams.items():
            ranked = _simulate_group(
                g_teams,
                team_elo,
                fixed_by_group.get(grp, []),
                pending_by_group.get(grp, []),
                rng,
            )
            group_standings[grp] = ranked

        # Determine 32 qualifiers: 1st + 2nd from each group (24) + 8 best 3rd-place
        qualifiers: set[str] = set()
        third_place_pool: list[str] = []

        for _grp, ranked in group_standings.items():
            if len(ranked) >= 1:
                qualifiers.add(ranked[0])
            if len(ranked) >= 2:
                qualifiers.add(ranked[1])
            if len(ranked) >= 3:
                third_place_pool.append(ranked[2])

        # Shuffle for random tiebreak among 3rd-place teams, then take top 8
        rng.shuffle(third_place_pool)
        best_thirds = third_place_pool[:8]
        for t in best_thirds:
            qualifiers.add(t)

        # Award group qualification points
        for tid in qualifiers:
            if tid in team_owner:
                scores[team_owner[tid]] += GROUP_QUALIFICATION_POINTS

        # ---- Build R32 bracket ----
        # slots 0–11 (1-based slots 1–12): group winner/runner-up
        # slots 12–15 (1-based 13–16): best 3rd-place teams
        r32_matchups: list[tuple[str, str]] = []

        for i, (home_desc, away_desc) in enumerate(R32_SLOTS):
            if i < 12:
                h_grp, h_pos = home_desc
                a_grp, a_pos = away_desc
                pos_idx = {"1st": 0, "2nd": 1, "3rd": 2}
                home_team = group_standings.get(h_grp, ["?"] * 4)[pos_idx[h_pos]]
                away_team = group_standings.get(a_grp, ["?"] * 4)[pos_idx[a_pos]]
            else:
                # Slots 13–16: pair up best 3rd-place teams
                pair_idx = (i - 12) * 2
                home_team = best_thirds[pair_idx] if pair_idx < len(best_thirds) else "?"
                away_team = best_thirds[pair_idx + 1] if pair_idx + 1 < len(best_thirds) else "?"
            r32_matchups.append((home_team, away_team))

        # ---- Knockout simulation ----
        r32_winners = _sim_round(
            r32_matchups, "r32", scores, team_owner, team_elo, completed_knockout, rng
        )
        r16_matchups = [(r32_winners[a - 1], r32_winners[b - 1]) for a, b in R16_BRACKET]
        r16_winners = _sim_round(
            r16_matchups, "r16", scores, team_owner, team_elo, completed_knockout, rng
        )
        qf_matchups = [(r16_winners[a - 1], r16_winners[b - 1]) for a, b in QF_BRACKET]
        qf_winners = _sim_round(
            qf_matchups, "qf", scores, team_owner, team_elo, completed_knockout, rng
        )
        sf_matchups = [(qf_winners[a - 1], qf_winners[b - 1]) for a, b in SF_BRACKET]
        sf_winners = _sim_round(
            sf_matchups, "sf", scores, team_owner, team_elo, completed_knockout, rng
        )
        _sim_round(
            [(sf_winners[0], sf_winners[1])],
            "final",
            scores,
            team_owner,
            team_elo,
            completed_knockout,
            rng,
        )

        # ---- Rank participants this run ----
        sorted_pids = sorted(participant_ids, key=lambda pid: scores[pid], reverse=True)
        rank = 1
        for i, pid in enumerate(sorted_pids):
            if i > 0 and scores[pid] < scores[sorted_pids[i - 1]]:
                rank = i + 1
            rank_counts[pid][rank] += 1

    # ------------------------------------------------------------------
    # Build probabilities output
    # ------------------------------------------------------------------
    rank_labels = {1: "rank_1", 2: "rank_2", 3: "rank_3", 4: "rank_4", 5: "rank_5"}
    probabilities: dict[str, dict[str, float]] = {}
    for pid in participant_ids:
        probabilities[pid] = {
            rank_labels[r]: rank_counts[pid][r] / n_runs for r in range(1, len(participant_ids) + 1)
        }

    return SimulationRun(
        id="simulationRun_latest",
        run_at=datetime.now(UTC),
        matches_completed_at_run=completed_match_count,
        n_runs=n_runs,
        probabilities=probabilities,
    )
