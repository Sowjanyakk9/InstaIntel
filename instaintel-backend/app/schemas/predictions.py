from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel


class PredictionResponse(BaseModel):

    dataset_id: int

    forecast_json: Dict[str, Any]

    risk_score: float

    risk_factors_json: List[Dict[str, Any]]

    created_at: datetime

    class Config:
        orm_mode = True