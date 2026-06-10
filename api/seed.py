import json
from pathlib import Path

from api.models import Match, Participant, Team

_SEED_DIR = Path(__file__).parent.parent / "shared" / "seed"


def load_teams() -> list[Team]:
    data = json.loads((_SEED_DIR / "teams.json").read_text(encoding="utf-8"))
    return [Team.model_validate(t) for t in data]


def load_participants() -> list[Participant]:
    data = json.loads((_SEED_DIR / "participants.json").read_text(encoding="utf-8"))
    return [Participant.model_validate(p) for p in data]


def load_fixtures() -> list[Match]:
    data = json.loads((_SEED_DIR / "fixtures.json").read_text(encoding="utf-8"))
    return [Match.model_validate(f) for f in data]
