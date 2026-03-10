from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel


class DashboardWidgetConfig(BaseModel):
    chart_id: int | None = None
    kpi_name: str | None = None
    title: str
    subtitle: str | None = None
    filters: Dict[str, Any] | None = None
    source_type: str | None = None
    source_ids: List[int] | None = None
    payload: Dict[str, Any] | None = None


class DashboardWidgetResponse(BaseModel):
    id: int
    widget_type: str
    position: Dict[str, int]
    config_json: Dict[str, Any]
    created_at: datetime

    class Config:
        orm_mode = True


class DashboardResponse(BaseModel):
    dataset_id: int
    title: str
    layout_json: Dict[str, Any]
    widgets: List[DashboardWidgetResponse]
    created_at: datetime