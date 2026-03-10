from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String

from app.db.base import Base


class Chart(Base):
    __tablename__ = "charts"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    chart_type = Column(String, nullable=False)
    x_column = Column(String, nullable=False)
    y_column = Column(String, nullable=False)
    chart_config_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)