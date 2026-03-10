from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel


class RankedInsightSchema(BaseModel):
    insight_type: str
    title: str
    description: str
    priority_score: float
    evidence_refs: List[str]


class InsightStatsSchema(BaseModel):
    metrics: List[Dict[str, Any]]
    correlations: List[Dict[str, Any]]
    trends: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    drivers: List[Dict[str, Any]]


class InsightResponse(BaseModel):
    id: int
    dataset_id: int
    summary_text: str
    stats_json: Dict[str, Any]
    created_at: datetime

    class Config:
        orm_mode = True


class InsightStructuredResponse(BaseModel):
    dataset_id: int
    summary_text: str
    stats_json: Dict[str, Any]
    ranked_insights_json: List[RankedInsightSchema]
    created_at: datetime