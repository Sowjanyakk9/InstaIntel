from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.job_service import get_jobs
from app.db.session import get_db

router = APIRouter()


@router.get("/jobs/{dataset_id}")
def jobs(dataset_id: int,
         db: Session = Depends(get_db)):

    return get_jobs(db, dataset_id)