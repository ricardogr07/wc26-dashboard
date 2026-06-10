from __future__ import annotations

import json
import logging

import azure.functions as func

from api.cors import cors_headers
from api.cosmos import get_container
from api.models import Match, Participant, Team
from api.scoring import compute_scores

logger = logging.getLogger(__name__)


def handle_standings(req: func.HttpRequest) -> func.HttpResponse:
    try:
        container = get_container()
        participants = [
            Participant.model_validate(p)
            for p in container.query_items(
                query="SELECT * FROM c WHERE c.type = 'participant'",
                enable_cross_partition_query=True,
            )
        ]
        matches = [
            Match.model_validate(m)
            for m in container.query_items(
                query="SELECT * FROM c WHERE c.type = 'match'",
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
        logger.exception("Cosmos error in standings endpoint")
        return func.HttpResponse("Service unavailable", status_code=500, headers=cors_headers())

    scores = compute_scores(matches, participants, teams)
    team_by_id = {t.id: t for t in teams}
    sorted_participants = sorted(participants, key=lambda p: scores[p.id], reverse=True)

    standings = []
    rank = 1
    for i, p in enumerate(sorted_participants):
        if i > 0 and scores[p.id] < scores[sorted_participants[i - 1].id]:
            rank = i + 1
        standings.append(
            {
                "rank": rank,
                "participantId": p.id,
                "displayName": p.display_name,
                "score": scores[p.id],
                "teams": [
                    {
                        "teamId": tid,
                        "name": team_by_id[tid].name if tid in team_by_id else tid,
                        "group": team_by_id[tid].group if tid in team_by_id else None,
                        "status": team_by_id[tid].status if tid in team_by_id else "active",
                        "eloRating": team_by_id[tid].elo_rating if tid in team_by_id else None,
                    }
                    for tid in p.team_ids
                ],
            }
        )

    return func.HttpResponse(
        json.dumps({"standings": standings}),
        mimetype="application/json",
        status_code=200,
        headers=cors_headers(),
    )
