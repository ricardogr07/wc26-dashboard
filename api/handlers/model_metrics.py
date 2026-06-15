from __future__ import annotations

import json
import logging

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from api.cors import cors_headers
from api.cosmos import get_container

logger = logging.getLogger(__name__)


def handle_model_metrics(req: func.HttpRequest) -> func.HttpResponse:
    try:
        container = get_container()
        doc = container.read_item(item="modelMetrics_latest", partition_key="modelMetrics")
        return func.HttpResponse(
            json.dumps(doc),
            mimetype="application/json",
            status_code=200,
            headers=cors_headers(),
        )
    except CosmosResourceNotFoundError:
        return func.HttpResponse(
            json.dumps({"error": "No model has been trained yet"}),
            mimetype="application/json",
            status_code=404,
            headers=cors_headers(),
        )
    except Exception:
        logger.exception("Cosmos error in model_metrics endpoint")
        return func.HttpResponse("Service unavailable", status_code=503, headers=cors_headers())
