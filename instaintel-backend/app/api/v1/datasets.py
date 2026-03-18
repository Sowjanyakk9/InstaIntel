from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.db.rbac import get_current_user
from app.db.session import get_db

from app.models.alerts import Alert
from app.models.charts import Chart
from app.models.dashboards import Dashboard, DashboardWidget
from app.models.insights import Insight
from app.models.metadata import DatasetMetadata
from app.models.predictions import Prediction
from app.models.recommendations import Recommendation
from app.models.automation import AutomationRule, AutomationRunHistory
from app.models.notifications import NotificationRule, NotificationHistory

from app.schemas.alerts import AlertResponse
from app.schemas.charts import ChartListResponse
from app.schemas.dashboards import DashboardResponse
from app.schemas.insights import InsightStructuredResponse
from app.schemas.metadata import MetadataResponse
from app.schemas.predictions import PredictionResponse
from app.schemas.recommendations import RecommendationResponse
from app.schemas.automation import (
    AutomationRuleCreate,
    AutomationRuleUpdate,
    AutomationRuleResponse,
    AutomationRunHistoryResponse,
)
from app.schemas.notifications import (
    NotificationRuleCreate,
    NotificationRuleUpdate,
    NotificationRuleResponse,
    NotificationHistoryResponse,
)

from app.services.dataset_service import (
    create_dataset,
    delete_dataset,
    get_dataset,
    get_datasets,
)
from app.services.job_service import create_job
from app.services.storage_service import upload_file
from app.services.automation_service import (
    create_automation_rule,
    update_automation_rule,
    get_automation_rule,
    delete_automation_rule,
)
from app.services.notification_service import (
    create_notification_rule,
    update_notification_rule,
    get_notification_rule,
    delete_notification_rule,
)

from app.workers.tasks import dashboard_stage, run_pipeline

router = APIRouter()


# ---------------------------------------------------------
# Upload
# ---------------------------------------------------------

@router.post("/upload")
def upload(
    file: UploadFile,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, int]:
    path = upload_file(file)

    dataset = create_dataset(db, user.id, path, file.filename)
    job = create_job(db, dataset.id)

    run_pipeline.delay(dataset.id)

    return {"dataset_id": dataset.id, "job_id": job.id}


# ---------------------------------------------------------
# Dataset CRUD
# ---------------------------------------------------------

@router.get("/datasets")
def list_datasets(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return get_datasets(db, user.id)


@router.get("/dataset/{dataset_id}")
def dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    record = get_dataset(db, dataset_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return record


@router.delete("/dataset/{dataset_id}")
def delete(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    record = get_dataset(db, dataset_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return delete_dataset(db, dataset_id)


# ---------------------------------------------------------
# Metadata
# ---------------------------------------------------------

@router.get("/dataset/{dataset_id}/metadata", response_model=MetadataResponse)
def get_metadata(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    metadata = (
        db.query(DatasetMetadata)
        .filter(DatasetMetadata.dataset_id == dataset_id)
        .first()
    )
    if metadata is None:
        raise HTTPException(status_code=404, detail="Metadata not found")

    return metadata


# ---------------------------------------------------------
# Insights
# ---------------------------------------------------------

@router.get("/dataset/{dataset_id}/insights", response_model=InsightStructuredResponse)
def get_insights(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    insight = db.query(Insight).filter(Insight.dataset_id == dataset_id).first()
    if insight is None:
        raise HTTPException(status_code=404, detail="Insights not found")

    ranked_insights = insight.stats_json.get("ranked_insights_json", [])
    stats_json = {
        "metrics": insight.stats_json.get("metrics", []),
        "correlations": insight.stats_json.get("correlations", []),
        "trends": insight.stats_json.get("trends", []),
        "anomalies": insight.stats_json.get("anomalies", []),
        "drivers": insight.stats_json.get("drivers", []),
    }

    return {
        "dataset_id": insight.dataset_id,
        "summary_text": insight.summary_text,
        "stats_json": stats_json,
        "ranked_insights_json": ranked_insights,
        "created_at": insight.created_at,
    }


# ---------------------------------------------------------
# Charts
# ---------------------------------------------------------

@router.get("/dataset/{dataset_id}/charts", response_model=ChartListResponse)
def get_charts(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    charts = db.query(Chart).filter(Chart.dataset_id == dataset_id).all()
    if not charts:
        raise HTTPException(status_code=404, detail="Charts not found")

    return {
        "dataset_id": dataset_id,
        "chart_specs": [
            {
                "chart_type": chart.chart_type,
                "x_column": chart.x_column,
                "y_column": chart.y_column,
                "chart_config_json": chart.chart_config_json,
            }
            for chart in charts
        ],
    }


# ---------------------------------------------------------
# Predictions
# ---------------------------------------------------------

@router.get("/dataset/{dataset_id}/predictions", response_model=PredictionResponse)
def get_predictions(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    prediction = (
        db.query(Prediction)
        .filter(Prediction.dataset_id == dataset_id)
        .first()
    )
    if not prediction:
        raise HTTPException(status_code=404, detail="Predictions not found")

    return prediction


# ---------------------------------------------------------
# Alerts
# ---------------------------------------------------------

@router.get("/dataset/{dataset_id}/alerts", response_model=List[AlertResponse])
def get_alerts(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    alerts = db.query(Alert).filter(Alert.dataset_id == dataset_id).all()
    return alerts


# ---------------------------------------------------------
# Recommendations
# ---------------------------------------------------------

@router.get(
    "/dataset/{dataset_id}/recommendations",
    response_model=List[RecommendationResponse],
)
def get_recommendations(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    recommendations = (
        db.query(Recommendation)
        .filter(Recommendation.dataset_id == dataset_id)
        .all()
    )
    return recommendations


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

@router.get("/dataset/{dataset_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    dashboard = (
        db.query(Dashboard)
        .filter(Dashboard.dataset_id == dataset_id)
        .first()
    )

    if dashboard is None:
        dashboard_stage.delay(dataset_id)
        raise HTTPException(
            status_code=404,
            detail="Dashboard not found. Assembly triggered.",
        )

    widgets = (
        db.query(DashboardWidget)
        .filter(DashboardWidget.dashboard_id == dashboard.id)
        .order_by(DashboardWidget.id.asc())
        .all()
    )

    return {
        "dataset_id": dataset_id,
        "title": dashboard.title,
        "layout_json": dashboard.layout_json,
        "widgets": widgets,
        "created_at": dashboard.created_at,
    }


# ---------------------------------------------------------
# Automation Rules
# ---------------------------------------------------------

@router.post(
    "/dataset/{dataset_id}/automation",
    response_model=AutomationRuleResponse,
)
def create_automation_rule_endpoint(
    dataset_id: int,
    data: AutomationRuleCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return create_automation_rule(db, dataset_id, data)


@router.get(
    "/dataset/{dataset_id}/automation",
    response_model=AutomationRuleResponse,
)
def get_automation_rule_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    rule = get_automation_rule(db, dataset_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")

    return rule


@router.put(
    "/dataset/{dataset_id}/automation",
    response_model=AutomationRuleResponse,
)
def update_automation_rule_endpoint(
    dataset_id: int,
    data: AutomationRuleUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    rule = get_automation_rule(db, dataset_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")

    return update_automation_rule(db, rule, data)


@router.delete("/dataset/{dataset_id}/automation")
def delete_automation_rule_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    rule = get_automation_rule(db, dataset_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")

    delete_automation_rule(db, rule)

    return {"status": "deleted"}


@router.get(
    "/dataset/{dataset_id}/automation/history",
    response_model=List[AutomationRunHistoryResponse],
)
def automation_history(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if dataset_record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    history = (
        db.query(AutomationRunHistory)
        .filter(AutomationRunHistory.dataset_id == dataset_id)
        .order_by(AutomationRunHistory.started_at.desc())
        .all()
    )

    return history


# ---------------------------------------------------------
# Notification Rules
# ---------------------------------------------------------

@router.post(
    "/dataset/{dataset_id}/notifications",
    response_model=NotificationRuleResponse,
)
def create_notification_rule_endpoint(
    dataset_id: int,
    data: NotificationRuleCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if not dataset_record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return create_notification_rule(db, dataset_id, data)


@router.get(
    "/dataset/{dataset_id}/notifications",
    response_model=NotificationRuleResponse,
)
def get_notification_rule_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if not dataset_record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    rule = get_notification_rule(db, dataset_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Notification rule not found")

    return rule


@router.put(
    "/dataset/{dataset_id}/notifications",
    response_model=NotificationRuleResponse,
)
def update_notification_rule_endpoint(
    dataset_id: int,
    data: NotificationRuleUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if not dataset_record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    rule = get_notification_rule(db, dataset_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Notification rule not found")

    return update_notification_rule(db, rule, data)


@router.delete("/dataset/{dataset_id}/notifications")
def delete_notification_rule_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if not dataset_record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    rule = get_notification_rule(db, dataset_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Notification rule not found")

    delete_notification_rule(db, rule)

    return {"status": "deleted"}


@router.get(
    "/dataset/{dataset_id}/notifications/history",
    response_model=List[NotificationHistoryResponse],
)
def notification_history_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    dataset_record = get_dataset(db, dataset_id)
    if not dataset_record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    history = (
        db.query(NotificationHistory)
        .filter(NotificationHistory.dataset_id == dataset_id)
        .order_by(NotificationHistory.sent_at.desc())
        .all()
    )

    return history
