from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey

from app.db.base import Base


class NotificationRule(Base):

    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True)

    notification_enabled = Column(Boolean, default=True)

    channels = Column(JSON)  # ["email", "slack", "teams"]

    frequency = Column(String)  # immediate / daily / weekly

    triggers_json = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)


class NotificationHistory(Base):

    __tablename__ = "notification_history"

    id = Column(Integer, primary_key=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True)

    channel = Column(String)

    trigger = Column(String)

    content_summary = Column(String)

    sent_at = Column(DateTime)

    status = Column(String)

    error_message = Column(String)