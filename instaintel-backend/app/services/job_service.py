from sqlalchemy.orm import Session
from app.models.jobs import ProcessingJob


def create_job(db: Session, dataset_id: int):

    job = ProcessingJob(
        dataset_id=dataset_id,
        stage="upload_received",
        status="pending",
        progress=0
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def get_jobs(db: Session, dataset_id: int):

    return db.query(ProcessingJob).filter(
        ProcessingJob.dataset_id == dataset_id
    ).all()