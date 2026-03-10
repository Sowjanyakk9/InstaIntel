from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime
from app.db.base import Base


class Dataset(Base):

    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    file_path = Column(String)

    file_type = Column(String)

    upload_time = Column(DateTime, default=datetime.utcnow)

    status = Column(String)