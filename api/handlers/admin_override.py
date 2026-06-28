from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from api.cosmos import get_container

logger = logging.getLogger(__name__)


def handle_admin_override(req: func.HttpRequest) -> func.HttpResponse:
    expected_key = os.environ.get("ADMIN_API_KEY", "")
    provided_key = req.headers.get("x-functions-key", "")
    if not expected_key or provided_key != expected_key:
        return func.HttpResponse("Unauthorized", status_code=401)

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    _missing = object()
    match_id = body.get("matchId")
    home_score = body.get("homeScore")
    away_score = body.get("awayScore")
    winner_id = body.get("winnerId", _missing)

    if any(v is None for v in [match_id, home_score, away_score]) or winner_id is _missing:
        return func.HttpResponse(
            "Missing required fields: matchId, homeScore, awayScore, winnerId",
            status_code=400,
        )
    if not isinstance(home_score, int) or not isinstance(away_score, int):
        return func.HttpResponse("homeScore and awayScore must be integers", status_code=400)
    if home_score < 0 or away_score < 0:
        return func.HttpResponse("homeScore and awayScore must be non-negative", status_code=400)

    try:
        container = get_container()

        try:
            match_doc = container.read_item(item=match_id, partition_key="match")
        except CosmosResourceNotFoundError:
            return func.HttpResponse(f"Match '{match_id}' not found", status_code=404)

        if winner_id is None and home_score != away_score:
            return func.HttpResponse(
                "winnerId may only be null when scores are equal (draw)",
                status_code=400,
            )
        if winner_id is not None and winner_id not in (
            match_doc.get("homeTeamId"),
            match_doc.get("awayTeamId"),
        ):
            return func.HttpResponse(
                "winnerId must be homeTeamId or awayTeamId of the specified match (or null for a draw)",
                status_code=400,
            )

        now_iso = datetime.now(UTC).isoformat()
        container.patch_item(
            item=match_id,
            partition_key="match",
            patch_operations=[
                {"op": "set", "path": "/homeScore", "value": home_score},
                {"op": "set", "path": "/awayScore", "value": away_score},
                {"op": "set", "path": "/winnerId", "value": winner_id},
                {"op": "set", "path": "/status", "value": "completed"},
                {"op": "set", "path": "/lastUpdated", "value": now_iso},
            ],
        )
        container.create_item(
            {
                "id": f"audit_{uuid.uuid4().hex}",
                "type": "audit",
                "action": "override",
                "matchId": match_id,
                "homeScore": home_score,
                "awayScore": away_score,
                "winnerId": winner_id,
                "appliedAt": now_iso,
            }
        )
    except Exception:
        logger.exception("Cosmos error in admin override endpoint")
        return func.HttpResponse("Service unavailable", status_code=500)

    return func.HttpResponse(
        json.dumps({"matchId": match_id, "status": "updated"}),
        mimetype="application/json",
        status_code=200,
    )
