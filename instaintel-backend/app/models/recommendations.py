from datetime import datetime
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from app.db.base import Base


class Recommendation(Base):

    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True)

    recommendation_type = Column(String)

    priority = Column(Integer)

    title = Column(String)

    description = Column(String)

    evidence_json = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)