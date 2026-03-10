from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, String, Float, DateTime
from app.db.base import Base


class MLModel(Base):

    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id"))

    model_type = Column(String)

    model_path = Column(String)

    accuracy = Column(Float)

    trained_at = Column(DateTime, default=datetime.utcnow)