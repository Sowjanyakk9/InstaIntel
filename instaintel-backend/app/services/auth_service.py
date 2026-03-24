from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.users import User
from app.core.security import hash_password, verify_password


def register_user(db: Session, name: str, email: str, password: str):
    existing_user = db.query(User).filter(User.email == email).first()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user