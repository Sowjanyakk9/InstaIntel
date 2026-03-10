from sqlalchemy.orm import Session
from app.models.users import User


def get_user(db: Session, user_id: int):

    return db.query(User).filter(User.id == user_id).first()