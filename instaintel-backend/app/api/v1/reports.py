from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.reports import ReportJob
from app.schemas.reports import ReportJobResponse

router = APIRouter()

@router.get("/dataset/{dataset_id}/reports", response_model=list[ReportJobResponse])
def list_reports(dataset_id: int, db: Session = Depends(get_db)):
    return db.query(ReportJob).filter(ReportJob.dataset_id == dataset_id).order_by(ReportJob.created_at.desc()).all()