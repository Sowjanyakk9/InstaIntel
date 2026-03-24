from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.db.base import Base
from app.db.session import engine

# optional model imports if needed for table creation side effects
from app.models.alerts import Alert  # noqa: F401
from app.models.charts import Chart  # noqa: F401
from app.models.dashboards import Dashboard, DashboardWidget  # noqa: F401
from app.models.datasets import Dataset  # noqa: F401
from app.models.insights import Insight  # noqa: F401
from app.models.jobs import ProcessingJob  # noqa: F401
from app.models.logs import Log  # noqa: F401
from app.models.metadata import DatasetMetadata  # noqa: F401
from app.models.ml_models import MLModel  # noqa: F401
from app.models.predictions import Prediction  # noqa: F401
from app.models.recommendations import Recommendation  # noqa: F401
from app.models.roles import Role, UserRole  # noqa: F401
from app.models.users import User  # noqa: F401

app = FastAPI(title="InstaIntel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-frontend-domain.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
def root():
    return {"status": "ok", "service": "InstaIntel API"}

# optional
Base.metadata.create_all(bind=engine)