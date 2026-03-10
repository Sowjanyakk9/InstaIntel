from datetime import datetime
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from app.db.base import Base


class Alert(Base):

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True)

    alert_type = Column(String)

    severity = Column(String)

    title = Column(String)

    description = Column(String)

    evidence_json = Column(JSON)

    recommended_action = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)