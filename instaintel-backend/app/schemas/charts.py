from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel


class ChartSpecSchema(BaseModel):
    chart_type: str
    x_column: str
    y_column: str
    chart_config_json: Dict[str, Any]


class ChartResponse(BaseModel):
    id: int
    dataset_id: int
    chart_type: str
    x_column: str
    y_column: str
    chart_config_json: Dict[str, Any]
    created_at: datetime

    class Config:
        orm_mode = True


class ChartListResponse(BaseModel):
    dataset_id: int
    chart_specs: List[ChartSpecSchema]