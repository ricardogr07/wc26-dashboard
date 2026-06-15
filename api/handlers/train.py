from __future__ import annotations

import json
import logging

import azure.functions as func

from api.cors import cors_headers
from api.cosmos import get_container
from api.ml.predictor import get_model_path
from api.ml.trainer import train_and_save
from api.models import Match, Team
from api.seed import load_teams

logger = logging.getLogger(__name__)


def handle_train(req: func.HttpRequest) -> func.HttpResponse:
    try:
        container = get_container()
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
        logger.exception("Cosmos error in train endpoint")
        return func.HttpResponse("Service unavailable", status_code=503, headers=cors_headers())

    if not teams:
        teams = load_teams()

    try:
        result = train_and_save(matches, teams, get_model_path())
    except ValueError as exc:
        return func.HttpResponse(str(exc), status_code=422, headers=cors_headers())
    except RuntimeError as exc:
        return func.HttpResponse(str(exc), status_code=501, headers=cors_headers())
    except Exception:
        logger.exception("Training failed")
        return func.HttpResponse("Training failed", status_code=500, headers=cors_headers())

    metrics_doc = {
        "id": "modelMetrics_latest",
        "type": "modelMetrics",
        "nSamples": result.n_samples,
        "logLoss": result.log_loss,
        "brierScore": result.brier_score,
        "eloLogLoss": result.elo_log_loss,
        "eloBrierScore": result.elo_brier_score,
        "modelBeatsElo": result.model_beats_elo,
    }
    try:
        container.upsert_item(metrics_doc)
    except Exception:
        logger.warning("Failed to persist model metrics to Cosmos", exc_info=True)

    return func.HttpResponse(
        json.dumps(metrics_doc),
        mimetype="application/json",
        status_code=200,
        headers=cors_headers(),
    )
