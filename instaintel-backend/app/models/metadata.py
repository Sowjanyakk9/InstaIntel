from sqlalchemy import Column, Integer, ForeignKey, DateTime, JSON, String
from datetime import datetime
from app.db.base import Base


class DatasetMetadata(Base):

    __tablename__ = "dataset_metadata"

    id = Column(Integer, primary_key=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id"))

    columns_json = Column(JSON)

    metrics_json = Column(JSON)

    dimensions_json = Column(JSON)

    time_columns_json = Column(JSON)

    text_columns_json = Column(JSON)

    id_columns_json = Column(JSON)

    domain_detected = Column(String)

    primary_kpis_json = Column(JSON)

    analysis_plan_json = Column(JSON)

    row_count = Column(Integer)

    column_count = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
    