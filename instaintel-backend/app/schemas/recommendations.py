from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel


class RecommendationResponse(BaseModel):

    id: int
    dataset_id: int
    recommendation_type: str
    priority: int
    title: str
    description: str
    evidence_json: Dict[str, Any]
    created_at: datetime

    class Config:
        orm_mode = True