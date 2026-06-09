from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MatchRound = Literal["group", "r32", "r16", "qf", "sf", "final"]
MatchStatus = Literal["scheduled", "live", "completed"]


class Match(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    type: Literal["match"] = "match"
    round: MatchRound
    group: str | None = None
    home_team_id: str
    away_team_id: str
    scheduled_at: datetime
    venue: str | None = None
    home_score: int | None = None
    away_score: int | None = None
    winner_id: str | None = None
    status: MatchStatus = "scheduled"
    source: str
    last_updated: datetime
