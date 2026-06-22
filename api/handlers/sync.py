from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime, timedelta

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from api.cosmos import get_container
from api.sync_matches.elo_updater import compute_elo_update
from api.sync_matches.thesportsdb import (
    TSDB_TEAM_ALIASES,
    fetch_events_on_date,
    fetch_live_and_recent_events,
    fetch_season_events,
    parse_round,
    parse_scheduled_at,
    parse_score,
    parse_status,
)

logger = logging.getLogger(__name__)


def _build_team_name_map(container: ContainerProxy) -> dict[str, str]:
    """Return {team_name: team_id} by querying all team documents.

    Aliases for common TheSportsDB name variations (e.g. "Turkey" vs "Türkiye")
    are seeded first so that the authoritative DB name always wins on collision.
    """
    items = container.query_items(
        query="SELECT c.id, c.name FROM c WHERE c.type = 'team'",
        enable_cross_partition_query=True,
    )
    mapping: dict[str, str] = dict(TSDB_TEAM_ALIASES)
    for item in items:
        mapping[item["name"]] = item["id"]
    return mapping


def _determine_winner(
    home_score: int | None,
    away_score: int | None,
    home_id: str,
    away_id: str,
    raw_winner_name: str | None,
    team_id_by_name: dict[str, str],
) -> str | None:
    if raw_winner_name:
        resolved = team_id_by_name.get(raw_winner_name)
        if resolved:
            return resolved
        logger.warning("Cannot resolve winner name %r to a team ID", raw_winner_name)
    if home_score is None or away_score is None:
        return None
    if home_score > away_score:
        return home_id
    if away_score > home_score:
        return away_id
    return None  # draw — no winner (group stage)


def _result_changed(
    existing: dict,
    status: str,
    home_score: int | None,
    away_score: int | None,
    winner_id: str | None,
) -> bool:
    return (
        existing.get("status") != status
        or existing.get("homeScore") != home_score
        or existing.get("awayScore") != away_score
        or existing.get("winnerId") != winner_id
    )


def _find_existing_match(container: ContainerProxy, home_id: str, away_id: str) -> dict | None:
    """Find a match document by team pair regardless of its ID prefix."""
    items = list(
        container.query_items(
            query=(
                "SELECT * FROM c WHERE c.type = 'match'"
                " AND c.homeTeamId = @home AND c.awayTeamId = @away"
            ),
            parameters=[
                {"name": "@home", "value": home_id},
                {"name": "@away", "value": away_id},
            ],
            enable_cross_partition_query=True,
        )
    )
    return items[0] if items else None


def _process_event(
    container: ContainerProxy,
    event: dict,
    team_id_by_name: dict[str, str],
    now_iso: str,
    counts: dict[str, int],
) -> None:
    event_id = event.get("idEvent", "")
    match_id = f"tsdb_{event_id}"

    home_score = parse_score(event.get("intHomeScore"))
    away_score = parse_score(event.get("intAwayScore"))
    raw_status = event.get("strStatus") or event.get("strProgress") or ""
    status = parse_status(raw_status)
    if home_score is not None and away_score is not None:
        if status == "scheduled":
            status = "completed"
        elif status == "live":
            # TheSportsDB sometimes keeps reporting "live" after a match ends;
            # if scores are set and the match started >3 hours ago, treat it as done.
            scheduled_at_dt = parse_scheduled_at(event.get("dateEvent"), event.get("strTime"))
            if datetime.now(UTC) - scheduled_at_dt > timedelta(hours=3):
                status = "completed"
    raw_winner_name = event.get("strWinner") or ""

    just_completed = False

    try:
        existing = container.read_item(item=match_id, partition_key="match")
        home_id: str = existing.get("homeTeamId", "")
        away_id: str = existing.get("awayTeamId", "")
        winner_id = _determine_winner(
            home_score, away_score, home_id, away_id, raw_winner_name, team_id_by_name
        )

        if not _result_changed(existing, status, home_score, away_score, winner_id):
            counts["skipped"] += 1
            return

        container.patch_item(
            item=match_id,
            partition_key="match",
            patch_operations=[
                {"op": "set", "path": "/status", "value": status},
                {"op": "set", "path": "/homeScore", "value": home_score},
                {"op": "set", "path": "/awayScore", "value": away_score},
                {"op": "set", "path": "/winnerId", "value": winner_id},
                {"op": "set", "path": "/lastUpdated", "value": now_iso},
            ],
        )
        just_completed = existing.get("status") != "completed" and status == "completed"

    except CosmosResourceNotFoundError:
        home_name = event.get("strHomeTeam", "")
        away_name = event.get("strAwayTeam", "")
        home_id = team_id_by_name.get(home_name, "")
        away_id = team_id_by_name.get(away_name, "")

        if not home_id or not away_id:
            logger.warning(
                "Cannot resolve teams for event %s: %r vs %r; skipping",
                event_id,
                home_name,
                away_name,
            )
            counts["skipped"] += 1
            return

        winner_id = _determine_winner(
            home_score, away_score, home_id, away_id, raw_winner_name, team_id_by_name
        )

        # Before creating a new tsdb_XXX document, check whether a seeded match
        # with a different ID (e.g. wiki_XXX) already exists for this team pair.
        existing_by_teams = _find_existing_match(container, home_id, away_id)
        if existing_by_teams:
            match_id = existing_by_teams["id"]
            if not _result_changed(existing_by_teams, status, home_score, away_score, winner_id):
                counts["skipped"] += 1
                return
            container.patch_item(
                item=match_id,
                partition_key="match",
                patch_operations=[
                    {"op": "set", "path": "/status", "value": status},
                    {"op": "set", "path": "/homeScore", "value": home_score},
                    {"op": "set", "path": "/awayScore", "value": away_score},
                    {"op": "set", "path": "/winnerId", "value": winner_id},
                    {"op": "set", "path": "/lastUpdated", "value": now_iso},
                ],
            )
            just_completed = (
                existing_by_teams.get("status") != "completed" and status == "completed"
            )
        else:
            scheduled_at = parse_scheduled_at(event.get("dateEvent"), event.get("strTime"))
            container.upsert_item(
                {
                    "id": match_id,
                    "type": "match",
                    "round": parse_round(event.get("strRound")),
                    "group": None,
                    "homeTeamId": home_id,
                    "awayTeamId": away_id,
                    "scheduledAt": scheduled_at.isoformat(),
                    "venue": event.get("strVenue") or None,
                    "homeScore": home_score,
                    "awayScore": away_score,
                    "winnerId": winner_id,
                    "status": status,
                    "source": "thesportsdb",
                    "lastUpdated": now_iso,
                }
            )
            just_completed = status == "completed"

    container.create_item(
        {
            "id": f"audit_{uuid.uuid4().hex}",
            "type": "audit",
            "action": "sync_upsert",
            "matchId": match_id,
            "status": status,
            "appliedAt": now_iso,
        }
    )
    counts["updated"] += 1

    if just_completed and winner_id:
        _update_elo(container, match_id, winner_id, home_id, away_id, now_iso, counts)


def _update_elo(
    container: ContainerProxy,
    match_id: str,
    winner_id: str,
    home_id: str,
    away_id: str,
    now_iso: str,
    counts: dict[str, int],
) -> None:
    loser_id = away_id if winner_id == home_id else home_id
    try:
        winner_doc = container.read_item(item=winner_id, partition_key="team")
        loser_doc = container.read_item(item=loser_id, partition_key="team")
        new_winner_elo, new_loser_elo = compute_elo_update(
            float(winner_doc.get("eloRating", 1500.0)),
            float(loser_doc.get("eloRating", 1500.0)),
        )

        container.patch_item(
            item=winner_id,
            partition_key="team",
            patch_operations=[{"op": "set", "path": "/eloRating", "value": new_winner_elo}],
        )
        container.patch_item(
            item=loser_id,
            partition_key="team",
            patch_operations=[{"op": "set", "path": "/eloRating", "value": new_loser_elo}],
        )
        container.create_item(
            {
                "id": f"audit_{uuid.uuid4().hex}",
                "type": "audit",
                "action": "elo_update",
                "matchId": match_id,
                "winnerId": winner_id,
                "loserId": loser_id,
                "newWinnerElo": new_winner_elo,
                "newLoserElo": new_loser_elo,
                "appliedAt": now_iso,
            }
        )
        counts["elo_updated"] += 1
    except Exception:
        logger.exception(
            "Elo update failed for match %s (winner=%s loser=%s)", match_id, winner_id, loser_id
        )


def _backfill_stale_scheduled(
    container: ContainerProxy,
    league_id: str,
    api_key: str,
    team_id_by_name: dict[str, str],
    now_iso: str,
    counts: dict[str, int],
) -> None:
    """For matches still 'scheduled' but >3 hours past kick-off, look them up on
    TheSportsDB by date and patch any that now have results.

    This catches the coverage gap where eventspastleague.php only returns the
    most recent ~15 events; older completed matches fall out of that window.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=3)

    stale: list[dict] = list(
        container.query_items(
            query=(
                "SELECT * FROM c WHERE c.type = 'match'"
                " AND c.status = 'scheduled'"
                " AND c.scheduledAt < @cutoff"
            ),
            parameters=[{"name": "@cutoff", "value": cutoff.isoformat()}],
            enable_cross_partition_query=True,
        )
    )

    if not stale:
        return

    # Group by calendar date (UTC) to minimise API calls
    by_date: dict[str, list[dict]] = {}
    for m in stale:
        date_key = (m.get("scheduledAt") or "")[:10]  # "YYYY-MM-DD"
        if date_key:
            by_date.setdefault(date_key, []).append(m)

    logger.info(
        "Backfill: %d stale-scheduled match(es) across %d date(s)", len(stale), len(by_date)
    )

    for date_key, matches in by_date.items():
        events = fetch_events_on_date(date_key, league_id, api_key)
        if not events:
            logger.debug("Backfill: no TheSportsDB events for %s", date_key)
            continue

        # Index events by (homeTeamId, awayTeamId) after resolving team names
        event_by_teams: dict[tuple[str, str], dict] = {}
        for e in events:
            h = team_id_by_name.get(e.get("strHomeTeam", ""), "")
            a = team_id_by_name.get(e.get("strAwayTeam", ""), "")
            if h and a:
                event_by_teams[(h, a)] = e

        for match in matches:
            key = (match.get("homeTeamId", ""), match.get("awayTeamId", ""))
            event = event_by_teams.get(key)
            if not event:
                logger.debug(
                    "Backfill: no TheSportsDB result for %s vs %s on %s",
                    key[0],
                    key[1],
                    date_key,
                )
                continue
            try:
                _process_event(container, event, team_id_by_name, now_iso, counts)
            except Exception:
                logger.exception("Backfill: error processing event %s", event.get("idEvent"))
                counts["errors"] += 1


def handle_sync(timer: func.TimerRequest) -> None:
    league_id = os.environ.get("THESPORTSDB_LEAGUE_ID", "4429")
    season = os.environ.get("THESPORTSDB_SEASON", "2026-2027")
    api_key = os.environ.get("THESPORTSDB_API_KEY", "3")

    season_year = int(season.split("-")[0]) if "-" in season else 2026
    events = fetch_live_and_recent_events(league_id, api_key, season_year=season_year)
    if not events:
        # Fall back to full-season endpoint (works with paid key)
        events = fetch_season_events(league_id, season, api_key)
    if not events:
        logger.warning("No events returned from TheSportsDB; aborting sync")
        return

    container = get_container()
    team_id_by_name = _build_team_name_map(container)
    now_iso = datetime.now(UTC).isoformat()
    counts: dict[str, int] = {"updated": 0, "skipped": 0, "elo_updated": 0, "errors": 0}

    for event in events:
        event_id = event.get("idEvent", "")
        if not event_id:
            counts["skipped"] += 1
            continue
        try:
            _process_event(container, event, team_id_by_name, now_iso, counts)
        except Exception:
            logger.exception("Unexpected error processing event %s", event_id)
            counts["errors"] += 1

    # Sweep any matches still stuck as 'scheduled' past their kick-off window
    _backfill_stale_scheduled(container, league_id, api_key, team_id_by_name, now_iso, counts)

    logger.info(
        "Sync complete — updated=%d skipped=%d elo_updated=%d errors=%d",
        counts["updated"],
        counts["skipped"],
        counts["elo_updated"],
        counts["errors"],
    )
