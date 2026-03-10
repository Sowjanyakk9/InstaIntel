from sqlalchemy.orm import Session
from app.models.datasets import Dataset


def create_dataset(db: Session, user_id: int, path: str, file_type: str):

    dataset = Dataset(
        user_id=user_id,
        file_path=path,
        file_type=file_type,
        status="uploaded"
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset


def get_datasets(db: Session, user_id: int):

    return db.query(Dataset).filter(Dataset.user_id == user_id).all()


def get_dataset(db: Session, dataset_id: int):

    return db.query(Dataset).filter(Dataset.id == dataset_id).first()


def delete_dataset(db: Session, dataset_id: int):

    dataset = get_dataset(db, dataset_id)

    if dataset:
        db.delete(dataset)
        db.commit()

    return dataset