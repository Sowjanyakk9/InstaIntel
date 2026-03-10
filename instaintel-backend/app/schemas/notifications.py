from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel


class NotificationRuleCreate(BaseModel):

    notification_enabled: bool = True

    channels: List[str]

    frequency: str

    triggers_json: Dict[str, Any] | None = None


class NotificationRuleUpdate(BaseModel):

    notification_enabled: bool | None = None

    channels: List[str] | None = None

    frequency: str | None = None

    triggers_json: Dict[str, Any] | None = None


class NotificationRuleResponse(BaseModel):

    id: int

    dataset_id: int

    notification_enabled: bool

    channels: List[str]

    frequency: str

    triggers_json: Dict[str, Any] | None

    created_at: datetime

    class Config:
        orm_mode = True


class NotificationHistoryResponse(BaseModel):

    id: int

    dataset_id: int

    channel: str

    trigger: str

    content_summary: str

    sent_at: datetime

    status: str

    error_message: str | None

    class Config:
        orm_mode = True