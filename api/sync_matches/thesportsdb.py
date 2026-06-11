from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.thesportsdb.com/api/v1/json"

_STATUS_MAP: dict[str, Literal["scheduled", "live", "completed"]] = {
    "match finished": "completed",
    "ft": "completed",
    "ap": "completed",   # after penalties
    "aet": "completed",  # after extra time
    "in progress": "live",
    "1h": "live",
    "2h": "live",
    "ht": "live",
    "et": "live",
    "pen": "live",
}

_ROUND_MAP: dict[str, Literal["group", "r32", "r16", "qf", "sf", "final"]] = {
    "round of 32": "r32",
    "round of 16": "r16",
    "quarter final": "qf",
    "quarter-final": "qf",
    "semi final": "sf",
    "semi-final": "sf",
    "final": "final",
}


def fetch_season_events(league_id: str, season: str, api_key: str) -> list[dict]:
    """Fetch all events for a league season from the TheSportsDB v1 API."""
    url = f"{_BASE_URL}/{api_key}/eventsseason.php"
    try:
        resp = httpx.get(url, params={"id": league_id, "s": season}, timeout=30.0)
        resp.raise_for_status()
        return resp.json().get("events") or []
    except Exception:
        logger.exception("TheSportsDB fetch failed for league=%s season=%s", league_id, season)
        return []


def fetch_live_and_recent_events(league_id: str, api_key: str) -> list[dict]:
    """Fetch current/upcoming and recently completed events for live score sync.

    eventsseason.php is gated behind a paid key for active seasons; these two
    endpoints work with the free key and cover everything needed for live updates.
    """
    seen: set[str] = set()
    events: list[dict] = []
    for endpoint in ("eventsnextleague.php", "eventspastleague.php"):
        url = f"{_BASE_URL}/{api_key}/{endpoint}"
        try:
            resp = httpx.get(url, params={"id": league_id}, timeout=30.0)
            resp.raise_for_status()
            for e in resp.json().get("events") or []:
                eid = e.get("idEvent", "")
                if eid and eid not in seen:
                    seen.add(eid)
                    events.append(e)
        except Exception:
            logger.exception("TheSportsDB fetch failed for %s league=%s", endpoint, league_id)
    return events


def parse_score(raw: object) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


def parse_status(raw: str | None) -> Literal["scheduled", "live", "completed"]:
    if not raw:
        return "scheduled"
    return _STATUS_MAP.get(raw.lower().strip(), "scheduled")


def parse_round(raw: str | None) -> Literal["group", "r32", "r16", "qf", "sf", "final"]:
    if not raw:
        return "group"
    return _ROUND_MAP.get(raw.lower().strip(), "group")


def parse_scheduled_at(date_str: str | None, time_str: str | None) -> datetime:
    try:
        d = date_str or "2026-01-01"
        t = time_str or "00:00:00"
        return datetime.fromisoformat(f"{d}T{t}+00:00")
    except ValueError:
        return datetime.now(UTC)
