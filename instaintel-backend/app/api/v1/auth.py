from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.services.auth_service import register_user, authenticate_user
from app.core.db.security import create_access_token
from app.db.session import get_db

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):

    user = register_user(db, data.name, data.email, data.password)

    token = create_access_token({"sub": str(user.id)})

    return {"access_token": token}


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = authenticate_user(db, data.email, data.password)

    token = create_access_token({"sub": str(user.id)})

    return {"access_token": token}