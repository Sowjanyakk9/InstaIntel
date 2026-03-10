from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from app.db.base import Base


class AutomationRule(Base):

    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True)

    automation_enabled = Column(Boolean, default=True)

    refresh_frequency = Column(String)  # daily, weekly, monthly, cron

    cron_expression = Column(String)

    trigger_rules_json = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)


class AutomationRunHistory(Base):

    __tablename__ = "automation_run_history"

    id = Column(Integer, primary_key=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True)

    triggered_by = Column(String)  # manual / schedule / event

    status = Column(String)

    started_at = Column(DateTime)

    finished_at = Column(DateTime)

    error_message = Column(String)