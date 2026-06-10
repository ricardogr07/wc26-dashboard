from __future__ import annotations

import json
import logging
from datetime import date

import azure.functions as func

from api.cosmos import get_container
from api.models import Match, Team

logger = logging.getLogger(__name__)

_VALID_ROUNDS = frozenset({"group", "r32", "r16", "qf", "sf", "final"})


def handle_matches(req: func.HttpRequest) -> func.HttpResponse:
    round_param = req.params.get("round")
    date_param = req.params.get("date")

    if round_param and round_param not in _VALID_ROUNDS:
        return func.HttpResponse(
            f"Invalid round '{round_param}', expected one of: {', '.join(sorted(_VALID_ROUNDS))}",
            status_code=400,
        )

    if date_param:
        try:
            date.fromisoformat(date_param)
        except ValueError:
            return func.HttpResponse(
                "Invalid date format, expected YYYY-MM-DD",
                status_code=400,
            )

    conditions = ["c.type = 'match'"]
    parameters: list[dict[str, object]] = []

    if round_param:
        conditions.append("c.round = @round")
        parameters.append({"name": "@round", "value": round_param})

    if date_param:
        conditions.append("STARTSWITH(c.scheduledAt, @date)")
        parameters.append({"name": "@date", "value": date_param})

    query = "SELECT * FROM c WHERE " + " AND ".join(conditions)

    try:
        container = get_container()
        matches = [
            Match.model_validate(m)
            for m in container.query_items(
                query=query,
                parameters=parameters if parameters else None,
                enable_cross_partition_query=True,
            )
        ]
        teams = [
            Team.model_validate(t)
            for t in container.query_items(
                query="SELECT * FROM c WHERE c.type = 'team'",
                enable_cross_partition_query=True,
            )
        ]
    except Exception:
        logger.exception("Cosmos error in matches endpoint")
        return func.HttpResponse("Service unavailable", status_code=500)

    team_by_id = {t.id: t for t in teams}
    matches.sort(key=lambda m: m.scheduled_at)

    result = []
    for m in matches:
        home = team_by_id.get(m.home_team_id)
        away = team_by_id.get(m.away_team_id)
        result.append(
            {
                "id": m.id,
                "round": m.round,
                "group": m.group,
                "homeTeam": {
                    "id": m.home_team_id,
                    "name": home.name if home else m.home_team_id,
                    "eloRating": home.elo_rating if home else None,
                },
                "awayTeam": {
                    "id": m.away_team_id,
                    "name": away.name if away else m.away_team_id,
                    "eloRating": away.elo_rating if away else None,
                },
                "scheduledAt": m.scheduled_at.isoformat(),
                "venue": m.venue,
                "homeScore": m.home_score,
                "awayScore": m.away_score,
                "winnerId": m.winner_id,
                "status": m.status,
            }
        )

    return func.HttpResponse(
        json.dumps({"matches": result}),
        mimetype="application/json",
        status_code=200,
    )
