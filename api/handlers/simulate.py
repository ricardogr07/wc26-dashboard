from __future__ import annotations

import json
import logging
from typing import cast

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from api.cors import cors_headers
from api.cosmos import get_container
from api.models import Match, Participant, Team
from api.seed import load_fixtures, load_participants, load_teams
from api.simulation.engine import run_simulation

logger = logging.getLogger(__name__)


def handle_simulate(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        body = {}

    overrides: list[dict] = body.get("overrides", []) if isinstance(body, dict) else []
    n_runs: int = int(body.get("nRuns", 10_000)) if isinstance(body, dict) else 10_000

    try:
        container = get_container()

        # Count completed matches for cache key
        count_result = list(
            container.query_items(
                query="SELECT VALUE COUNT(1) FROM c WHERE c.type='match' AND c.status='completed'",
                enable_cross_partition_query=True,
            )
        )
        completed_count: int = cast(int, count_result[0]) if count_result else 0

        # Serve cache when no overrides and match state is unchanged
        if not overrides:
            try:
                cached = container.read_item(
                    item="simulationRun_latest", partition_key="simulationRun"
                )
                if cached.get("matchesCompletedAtRun") == completed_count:
                    return func.HttpResponse(
                        json.dumps(cached),
                        mimetype="application/json",
                        status_code=200,
                        headers=cors_headers(),
                    )
            except CosmosResourceNotFoundError:
                pass

        # Load data
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
        logger.exception("Cosmos error in simulate endpoint")
        return func.HttpResponse("Service unavailable", status_code=500, headers=cors_headers())

    # Fall back to seed data when Cosmos has no data yet (pre-tournament)
    if not participants or not teams:
        participants = load_participants()
        teams = load_teams()
        if not matches:
            matches = load_fixtures()

    # Apply overrides to in-memory match list
    if overrides:
        override_map = {o["matchId"]: o for o in overrides if "matchId" in o}
        patched: list[Match] = []
        for m in matches:
            if m.id in override_map:
                o = override_map[m.id]
                patched.append(
                    m.model_copy(
                        update={
                            "status": "completed",
                            "winner_id": o.get("winnerId"),
                            "home_score": o.get("homeScore"),
                            "away_score": o.get("awayScore"),
                        }
                    )
                )
            else:
                patched.append(m)
        matches = patched

    try:
        result = run_simulation(matches, participants, teams, n_runs=n_runs)
    except Exception:
        logger.exception("run_simulation failed")
        return func.HttpResponse("Simulation error", status_code=500, headers=cors_headers())

    result_doc = result.model_dump(by_alias=True, mode="json")
    result_doc["type"] = "simulationRun"

    # Persist to Cosmos only for non-override runs (real-state cache)
    if not overrides:
        try:
            container.upsert_item(result_doc)
        except Exception:
            logger.warning("Failed to cache simulationRun to Cosmos", exc_info=True)

    return func.HttpResponse(
        json.dumps(result_doc),
        mimetype="application/json",
        status_code=200,
        headers=cors_headers(),
    )
