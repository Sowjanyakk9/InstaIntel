from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.datasets import Dataset
from app.models.jobs import ProcessingJob
from app.models.metadata import DatasetMetadata
from app.models.notifications import NotificationRule
from app.models.alerts import Alert
from app.models.predictions import Prediction
from app.models.insights import Insight

from app.services.dataset_understanding_service import (
    classify_columns,
    detect_kpis,
    generate_analysis_plan,
    infer_domain,
    save_metadata_to_db,
)
from app.services.insights_service import build_insights_output, save_insights_to_db
from app.services.charts_service import generate_chart_specs, save_chart_specs
from app.services.prediction_service import (
    compute_risk_score,
    run_regression_prediction,
    run_time_series_forecast,
    save_model_metadata_to_db,
    save_prediction_results_to_db,
    select_prediction_method,
)
from app.services.alerts_service import (
    generate_domain_alerts,
    generate_forecast_alerts,
    generate_kpi_alerts,
    generate_risk_alerts,
    rank_alerts,
    save_alerts_to_db,
)
from app.services.recommendation_service import (
    generate_domain_recommendations,
    generate_driver_recommendations,
    generate_forecast_recommendations,
    generate_kpi_recommendations,
    rank_recommendations,
    save_recommendations_to_db,
)
from app.services.dashboard_assembly_service import (
    build_dashboard_definition,
    save_dashboard_to_db,
)
from app.services.automation_service import run_automation_pipeline
from app.services.notification_service import (
    evaluate_notification_triggers,
    send_email_notification,
    send_slack_notification,
    send_teams_notification,
    log_notification_history,
)

from app.workers.queues import celery


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _load_dataset_frame(dataset: Dataset) -> pd.DataFrame:
    file_path = dataset.file_path
    file_type = (dataset.file_type or "").lower()

    if file_type.endswith("csv") or file_path.lower().endswith(".csv"):
        return pd.read_csv(file_path)

    if file_type.endswith(("xlsx", "xls")) or file_path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(file_path)

    if file_type.endswith("json") or file_path.lower().endswith(".json"):
        return pd.read_json(file_path)

    return pd.read_csv(file_path)


def _get_or_create_job(db: Session, dataset_id: int) -> ProcessingJob:
    job = db.query(ProcessingJob).filter_by(dataset_id=dataset_id).first()
    if job:
        return job

    job = ProcessingJob(
        dataset_id=dataset_id,
        stage="upload_received",
        status="pending",
        progress=0,
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _set_job_state(
    db: Session,
    job: ProcessingJob,
    stage: str,
    status: str,
    progress: int,
    error_message: Optional[str] = None,
) -> None:
    job.stage = stage
    job.status = status
    job.progress = progress
    job.error_message = error_message

    if status in {"completed", "failed", "partial", "skipped"}:
        job.finished_at = datetime.utcnow()

    db.commit()


# ---------------------------------------------------------
# Pipeline Orchestration
# ---------------------------------------------------------

@celery.task
def run_pipeline(dataset_id: int) -> None:
    cleaning_stage(dataset_id)
    dataset_understanding_stage(dataset_id)
    insights_stage(dataset_id)
    predictions_stage(dataset_id)
    alerts_stage(dataset_id)
    recommendations_stage(dataset_id)
    dashboard_stage(dataset_id)


# ---------------------------------------------------------
# Cleaning
# ---------------------------------------------------------

@celery.task
def cleaning_stage(dataset_id: int) -> None:
    db = SessionLocal()
    try:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "cleaning", "completed", 15)
    finally:
        db.close()


# ---------------------------------------------------------
# Dataset Understanding
# ---------------------------------------------------------

@celery.task
def dataset_understanding_stage(dataset_id: int) -> None:
    db = SessionLocal()
    try:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "dataset_understanding", "running", 20)

        dataset = db.query(Dataset).filter_by(id=dataset_id).first()
        if not dataset:
            raise ValueError("Dataset not found")

        df = _load_dataset_frame(dataset)

        classification = classify_columns(df)
        domain = infer_domain(classification["columns_json"])
        kpis = detect_kpis(df, classification, domain)
        analysis_plan = generate_analysis_plan(domain, kpis)

        save_metadata_to_db(
            db=db,
            dataset_id=dataset_id,
            classification=classification,
            domain=domain,
            kpis=kpis,
            analysis_plan=analysis_plan,
            row_count=df.shape[0],
            column_count=df.shape[1],
        )

        _set_job_state(db, job, "dataset_understanding", "completed", 40)

    except Exception as exc:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "dataset_understanding", "failed", job.progress, str(exc))
    finally:
        db.close()


# ---------------------------------------------------------
# Insights
# ---------------------------------------------------------

@celery.task
def insights_stage(dataset_id: int) -> None:
    db = SessionLocal()
    try:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "insights", "running", 50)

        dataset = db.query(Dataset).filter_by(id=dataset_id).first()
        metadata = db.query(DatasetMetadata).filter_by(dataset_id=dataset_id).first()

        if not dataset:
            raise ValueError("Dataset not found")
        if not metadata:
            raise ValueError("Metadata missing")

        df = _load_dataset_frame(dataset)

        insights_output = build_insights_output(
            df=df,
            metrics=metadata.metrics_json or [],
            dimensions=metadata.dimensions_json or [],
            time_columns=metadata.time_columns_json or [],
            primary_kpis=metadata.primary_kpis_json or [],
            domain=metadata.domain_detected or "generic",
        )

        stats_to_store = {
            "metrics": insights_output["stats_json"]["metrics"],
            "correlations": insights_output["stats_json"]["correlations"],
            "trends": insights_output["stats_json"]["trends"],
            "anomalies": insights_output["stats_json"]["anomalies"],
            "drivers": insights_output["stats_json"]["drivers"],
            "ranked_insights_json": insights_output["ranked_insights_json"],
        }

        save_insights_to_db(
            db=db,
            dataset_id=dataset_id,
            summary_text=insights_output["summary_text"],
            stats_json=stats_to_store,
        )

        chart_specs = generate_chart_specs(insights_output)
        save_chart_specs(db=db, dataset_id=dataset_id, chart_specs=chart_specs)

        _set_job_state(db, job, "insights", "completed", 60)

    except Exception as exc:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "insights", "failed", job.progress, str(exc))
    finally:
        db.close()


# ---------------------------------------------------------
# Predictions
# ---------------------------------------------------------

@celery.task
def predictions_stage(dataset_id: int) -> None:
    db = SessionLocal()
    try:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "predictions", "running", 70)

        dataset = db.query(Dataset).filter_by(id=dataset_id).first()
        metadata = db.query(DatasetMetadata).filter_by(dataset_id=dataset_id).first()
        insights = db.query(Insight).filter_by(dataset_id=dataset_id).first()

        if not dataset or not metadata or not insights:
            raise ValueError("Missing required data")

        df = _load_dataset_frame(dataset)

        method = select_prediction_method(metadata, insights)
        metrics = metadata.metrics_json or []
        kpi = metrics[0]

        if method == "time_series" and metadata.time_columns_json:
            result = run_time_series_forecast(df, kpi, metadata.time_columns_json[0])
            accuracy = 0.0
        else:
            result = run_regression_prediction(df, kpi)
            accuracy = result["model_quality"]["metric_value"]

        volatility = float(pd.to_numeric(df[kpi], errors="coerce").std())
        anomalies = len(insights.stats_json.get("anomalies", []))
        uncertainty = result.get("uncertainty", 0.0)

        risk_score = compute_risk_score(
            volatility=volatility,
            anomalies=anomalies,
            uncertainty=uncertainty,
            kpi_sensitivity=volatility,
        )

        risk_factors = [
            {"factor": "volatility", "score": volatility, "weight": 0.3},
            {"factor": "anomalies", "score": anomalies, "weight": 0.3},
            {"factor": "uncertainty", "score": uncertainty, "weight": 0.2},
            {"factor": "kpi_sensitivity", "score": volatility, "weight": 0.2},
        ]

        forecast_json = {
            "prediction_type": result["prediction_type"],
            "target_metric": result["target_metric"],
            "time_column": result.get("time_column"),
            "forecast_points": result.get("forecast_points", []),
            "feature_importance": result.get("feature_importance", []),
            "model_quality": result.get("model_quality", {"metric_value": accuracy}),
        }

        save_prediction_results_to_db(
            db=db,
            dataset_id=dataset_id,
            forecast_json=forecast_json,
            risk_score=risk_score,
            risk_factors=risk_factors,
        )

        save_model_metadata_to_db(
            db=db,
            dataset_id=dataset_id,
            model_type=result["prediction_type"],
            model=result["model"],
            accuracy=accuracy,
        )

        _set_job_state(db, job, "predictions", "completed", 80)

    except Exception as exc:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "predictions", "failed", job.progress, str(exc))
    finally:
        db.close()


# ---------------------------------------------------------
# Alerts
# ---------------------------------------------------------

@celery.task
def alerts_stage(dataset_id: int) -> None:
    db = SessionLocal()
    try:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "alerts", "running", 85)

        dataset = db.query(Dataset).filter_by(id=dataset_id).first()
        metadata = db.query(DatasetMetadata).filter_by(dataset_id=dataset_id).first()
        insights = db.query(Insight).filter_by(dataset_id=dataset_id).first()
        predictions = db.query(Prediction).filter_by(dataset_id=dataset_id).first()

        if not dataset or not metadata or not insights or not predictions:
            raise ValueError("Missing required data")

        df = _load_dataset_frame(dataset)

        alerts = []
        alerts.extend(generate_kpi_alerts(df, metadata, insights))
        alerts.extend(generate_forecast_alerts(predictions, metadata))
        alerts.extend(generate_risk_alerts(predictions, insights))
        alerts.extend(generate_domain_alerts(metadata.domain_detected, df, metadata, insights))

        ranked_alerts = rank_alerts(alerts)
        save_alerts_to_db(db, dataset_id, ranked_alerts)

        _set_job_state(db, job, "alerts", "completed", 90)

    except Exception as exc:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "alerts", "failed", job.progress, str(exc))
    finally:
        db.close()


# ---------------------------------------------------------
# Recommendations
# ---------------------------------------------------------

@celery.task
def recommendations_stage(dataset_id: int) -> None:
    db = SessionLocal()
    try:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "recommendations", "running", 95)

        metadata = db.query(DatasetMetadata).filter_by(dataset_id=dataset_id).first()
        insights = db.query(Insight).filter_by(dataset_id=dataset_id).first()
        predictions = db.query(Prediction).filter_by(dataset_id=dataset_id).first()

        if not metadata or not insights or not predictions:
            raise ValueError("Missing required data")

        recommendations = []
        recommendations.extend(generate_kpi_recommendations(metadata, insights))
        recommendations.extend(generate_driver_recommendations(insights))
        recommendations.extend(generate_forecast_recommendations(predictions))
        recommendations.extend(generate_domain_recommendations(metadata.domain_detected, insights, predictions))

        ranked_recommendations = rank_recommendations(recommendations)
        save_recommendations_to_db(db, dataset_id, ranked_recommendations)

        _set_job_state(db, job, "recommendations", "completed", 98)

    except Exception as exc:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "recommendations", "failed", job.progress, str(exc))
    finally:
        db.close()


# ---------------------------------------------------------
# Dashboard Assembly
# ---------------------------------------------------------

@celery.task
def dashboard_stage(dataset_id: int) -> None:
    db = SessionLocal()
    try:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "dashboard_assembly", "running", 99)

        dashboard_definition = build_dashboard_definition(dataset_id=dataset_id, db=db)
        save_dashboard_to_db(db=db, dataset_id=dataset_id, dashboard_definition=dashboard_definition)

        _set_job_state(db, job, "finished", "completed", 100)

    except Exception as exc:
        job = _get_or_create_job(db, dataset_id)
        _set_job_state(db, job, "dashboard_assembly", "failed", job.progress, str(exc))
    finally:
        db.close()


# ---------------------------------------------------------
# Automation Task
# ---------------------------------------------------------

@celery.task
def run_automation(dataset_id: int, triggered_by: str):
    db = SessionLocal()
    try:
        run_automation_pipeline(db, dataset_id, triggered_by)
    finally:
        db.close()


# ---------------------------------------------------------
# Notifications Task
# ---------------------------------------------------------

@celery.task
def run_notifications(dataset_id: int, triggered_by: str):
    db = SessionLocal()
    try:
        rule = db.query(NotificationRule).filter_by(dataset_id=dataset_id).first()

        if not rule or not rule.notification_enabled:
            return

        metadata = db.query(DatasetMetadata).filter_by(dataset_id=dataset_id).first()
        insights = db.query(Insight).filter_by(dataset_id=dataset_id).first()
        predictions = db.query(Prediction).filter_by(dataset_id=dataset_id).first()
        alerts = db.query(Alert).filter_by(dataset_id=dataset_id).all()

        triggers = evaluate_notification_triggers(
            dataset_id,
            metadata,
            insights,
            predictions,
            alerts,
            rule
        )

        if not triggers:
            return

        message = f"InstaIntel notification: dataset={dataset_id} triggers={triggers}"

        for channel in rule.channels:
            try:
                if channel == "email":
                    send_email_notification(rule, dataset_id, message)

                if channel == "slack":
                    send_slack_notification(rule, dataset_id, message)

                if channel == "teams":
                    send_teams_notification(rule, dataset_id, message)

                log_notification_history(
                    db,
                    dataset_id,
                    channel,
                    ",".join(triggers),
                    message,
                    "sent"
                )

            except Exception as e:
                log_notification_history(
                    db,
                    dataset_id,
                    channel,
                    ",".join(triggers),
                    message,
                    "failed",
                    str(e)
                )

    finally:
        db.close()
