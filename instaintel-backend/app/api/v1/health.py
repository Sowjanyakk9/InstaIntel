from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
def liveness():
    return {"status": "alive"}


@router.get("/ready")
def readiness():
    return {"status": "ready"}


@router.get("/")
def basic_health():
    return {"status": "ok"}