from api.models import Match, Participant, Team

ROUND_WIN_POINTS: dict[str, int] = {
    "r32": 2,
    "r16": 3,
    "qf": 5,
    "sf": 8,
    "final": 13,
}
GROUP_QUALIFICATION_POINTS = 1


def _build_team_owner(participants: list[Participant]) -> dict[str, str]:
    return {tid: p.id for p in participants for tid in p.team_ids}


def _award_group_qualification(
    matches: list[Match],
    team_owner: dict[str, str],
    scores: dict[str, int],
) -> None:
    # WC2026 r32 fixtures are only created after the group stage settles, so a
    # team appearing in any r32 match (even scheduled) has already qualified.
    # We guard with `qualified` because the same team could appear in two r32
    # rows if data is ever re-seeded or corrected.
    qualified: set[str] = set()
    for match in matches:
        if match.round != "r32":
            continue
        for tid in (match.home_team_id, match.away_team_id):
            if tid not in qualified and tid in team_owner:
                scores[team_owner[tid]] += GROUP_QUALIFICATION_POINTS
                qualified.add(tid)


def _award_knockout_wins(
    matches: list[Match],
    team_owner: dict[str, str],
    scores: dict[str, int],
) -> None:
    # Only completed matches with an explicit winner carry points. Knockout
    # matches always resolve to a winner (no draws), but we guard winner_id
    # explicitly so a data anomaly can't silently inflate scores.
    for match in matches:
        if (
            match.status == "completed"
            and match.winner_id is not None
            and match.round in ROUND_WIN_POINTS
            and match.winner_id in team_owner
        ):
            scores[team_owner[match.winner_id]] += ROUND_WIN_POINTS[match.round]


def compute_scores(
    matches: list[Match],
    participants: list[Participant],
    teams: list[Team],
) -> dict[str, int]:
    # `teams` is unused here but kept in the signature so callers (standings
    # endpoint, simulation engine) can pass the full data set without needing
    # a separate overload when team-level data becomes relevant in Phase 6.
    team_owner = _build_team_owner(participants)
    scores: dict[str, int] = {p.id: 0 for p in participants}
    _award_group_qualification(matches, team_owner, scores)
    _award_knockout_wins(matches, team_owner, scores)
    return scores
