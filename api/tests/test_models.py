import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from api.models import Match, Participant, SimulationRun, Team

# Minimal sentinel used only by validation-error tests that need a valid datetime.
_DT = datetime(2026, 6, 15, 19, 0, 0, tzinfo=UTC)

# ---------------------------------------------------------------------------
# Participant
# ---------------------------------------------------------------------------


def test_participant_roundtrip_dict(participant: Participant) -> None:
    restored = Participant.model_validate(participant.model_dump(by_alias=True))
    assert restored == participant


def test_participant_roundtrip_json(participant: Participant) -> None:
    restored = Participant.model_validate_json(participant.model_dump_json(by_alias=True))
    assert restored == participant


def test_participant_accepts_camelcase_input() -> None:
    doc = {
        "id": "ricardo",
        "type": "participant",
        "displayName": "Ricardo",
        "teamIds": ["MEX", "ARG", "GER", "NED", "SEN"],
    }
    p = Participant.model_validate(doc)
    assert p.display_name == "Ricardo"
    assert p.team_ids == ["MEX", "ARG", "GER", "NED", "SEN"]


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------


def test_team_roundtrip_dict(team: Team) -> None:
    restored = Team.model_validate(team.model_dump(by_alias=True))
    assert restored == team


def test_team_roundtrip_json(team: Team) -> None:
    restored = Team.model_validate_json(team.model_dump_json(by_alias=True))
    assert restored == team


def test_team_int_elo_coerced_to_float() -> None:
    t = Team(id="MEX", name="Mexico", group="C", elo_rating=1680)  # type: ignore[arg-type]
    assert isinstance(t.elo_rating, float)
    assert t.elo_rating == 1680.0


def test_team_invalid_status_raises() -> None:
    with pytest.raises(ValidationError):
        Team(id="MEX", name="Mexico", group="C", elo_rating=1680.0, status="winner")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------


def test_match_roundtrip_scheduled(scheduled_match: Match) -> None:
    assert scheduled_match.home_score is None
    assert scheduled_match.winner_id is None
    restored = Match.model_validate(scheduled_match.model_dump(by_alias=True))
    assert restored == scheduled_match


def test_match_roundtrip_completed(completed_match: Match) -> None:
    restored = Match.model_validate(completed_match.model_dump(by_alias=True))
    assert restored == completed_match
    assert restored.winner_id == "MEX"
    assert restored.home_score == 2


def test_match_datetime_serializes_to_iso(scheduled_match: Match) -> None:
    data = json.loads(scheduled_match.model_dump_json(by_alias=True))
    assert "scheduledAt" in data
    parsed = datetime.fromisoformat(data["scheduledAt"].replace("Z", "+00:00"))
    assert parsed == scheduled_match.scheduled_at


def test_match_invalid_round_raises() -> None:
    with pytest.raises(ValidationError):
        Match(
            id="x",
            round="semis",  # type: ignore[arg-type]
            home_team_id="MEX",
            away_team_id="POL",
            scheduled_at=_DT,
            source="thesportsdb",
            last_updated=_DT,
        )


def test_match_invalid_status_raises() -> None:
    with pytest.raises(ValidationError):
        Match(
            id="x",
            round="group",
            home_team_id="MEX",
            away_team_id="POL",
            scheduled_at=_DT,
            status="pending",  # type: ignore[arg-type]
            source="thesportsdb",
            last_updated=_DT,
        )


# ---------------------------------------------------------------------------
# SimulationRun
# ---------------------------------------------------------------------------


def test_simulation_run_roundtrip(simulation_run: SimulationRun) -> None:
    restored = SimulationRun.model_validate(simulation_run.model_dump(by_alias=True))
    assert restored == simulation_run


def test_simulation_run_probabilities_structure(simulation_run: SimulationRun) -> None:
    restored = SimulationRun.model_validate_json(simulation_run.model_dump_json(by_alias=True))
    assert restored.probabilities["ricardo"]["1st"] == pytest.approx(0.32)
    assert restored.probabilities["jibran"]["3rd"] == pytest.approx(0.24)
    assert set(restored.probabilities["ricardo"].keys()) == {"1st", "2nd", "3rd", "4th", "5th"}
