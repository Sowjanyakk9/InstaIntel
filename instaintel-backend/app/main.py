from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, datasets, jobs, users
from app.db.base import Base
from app.db.session import engine

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

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="InstaIntel API", version="1.0.0")

# -------------------------
# CORS MIDDLEWARE
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # In production, replace "*" with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# ROUTERS
# -------------------------
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(datasets.router, tags=["Datasets"])
app.include_router(jobs.router, tags=["Jobs"])

@app.get("/health")
def health():
    return {"status": "ok"}
