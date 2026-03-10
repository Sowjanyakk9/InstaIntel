from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, JSON, Float
from app.db.base import Base


class Prediction(Base):

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True)

    forecast_json = Column(JSON)

    risk_score = Column(Float)

    risk_factors_json = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)