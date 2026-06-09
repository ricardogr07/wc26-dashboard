from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SimulationRun(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    type: Literal["simulationRun"] = "simulationRun"
    run_at: datetime
    matches_completed_at_run: int
    n_runs: int
    probabilities: dict[str, dict[str, float]]
