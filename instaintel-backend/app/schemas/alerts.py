from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel


class AlertResponse(BaseModel):

    id: int
    dataset_id: int
    alert_type: str
    severity: str
    title: str
    description: str
    evidence_json: Dict[str, Any]
    recommended_action: str
    created_at: datetime

    class Config:
        orm_mode = True