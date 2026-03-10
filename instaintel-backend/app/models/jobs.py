from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime
from app.db.base import Base


class ProcessingJob(Base):

    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id"))

    stage = Column(String)

    status = Column(String)

    progress = Column(Integer)

    started_at = Column(DateTime, default=datetime.utcnow)

    finished_at = Column(DateTime)

    error_message = Column(String)