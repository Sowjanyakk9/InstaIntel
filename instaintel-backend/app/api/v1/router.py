from fastapi import APIRouter
from app.api.v1 import auth, datasets, jobs, users, health

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(datasets.router, tags=["datasets"])
api_router.include_router(jobs.router, tags=["jobs"])
api_router.include_router(health.router, tags=["health"])