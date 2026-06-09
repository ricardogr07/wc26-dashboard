from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

TeamStatus = Literal["active", "eliminated", "champion"]


class Team(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    type: Literal["team"] = "team"
    name: str
    group: str
    elo_rating: float
    status: TeamStatus = "active"
