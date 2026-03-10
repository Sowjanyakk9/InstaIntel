from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel


class AutomationRuleCreate(BaseModel):

    automation_enabled: bool = True

    refresh_frequency: str

    cron_expression: str | None = None

    trigger_rules_json: Dict[str, Any] | None = None


class AutomationRuleUpdate(BaseModel):

    automation_enabled: bool | None = None

    refresh_frequency: str | None = None

    cron_expression: str | None = None

    trigger_rules_json: Dict[str, Any] | None = None


class AutomationRuleResponse(BaseModel):

    id: int

    dataset_id: int

    automation_enabled: bool

    refresh_frequency: str

    cron_expression: str | None

    trigger_rules_json: Dict[str, Any] | None

    created_at: datetime

    class Config:
        orm_mode = True


class AutomationRunHistoryResponse(BaseModel):

    id: int

    dataset_id: int

    triggered_by: str

    status: str

    started_at: datetime

    finished_at: datetime | None

    error_message: str | None

    class Config:
        orm_mode = True