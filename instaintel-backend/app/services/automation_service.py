from datetime import datetime
from sqlalchemy.orm import Session

from app.models.automation import AutomationRule, AutomationRunHistory
from app.workers.tasks import run_pipeline, run_notifications


# -----------------------
# Rule Management
# -----------------------

def create_automation_rule(db: Session, dataset_id: int, data):
    rule = AutomationRule(
        dataset_id=dataset_id,
        automation_enabled=data.automation_enabled,
        refresh_frequency=data.refresh_frequency,
        cron_expression=data.cron_expression,
        trigger_rules_json=data.trigger_rules_json
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_automation_rule(db: Session, rule: AutomationRule, data):
    for field, value in data.dict(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


def get_automation_rule(db: Session, dataset_id: int):
    return db.query(AutomationRule).filter(
        AutomationRule.dataset_id == dataset_id
    ).first()


def delete_automation_rule(db: Session, rule: AutomationRule):
    db.delete(rule)
    db.commit()


# -----------------------
# Trigger Evaluation
# -----------------------

def evaluate_event_triggers(dataset_id, metadata, insights, predictions, alerts, rule):
    triggers = rule.trigger_rules_json or {}

    if "risk_threshold" in triggers:
        if predictions and predictions.risk_score > triggers["risk_threshold"]:
            return True

    if "anomaly_threshold" in triggers:
        anomalies = len(insights.stats_json.get("anomalies", []))
        if anomalies > triggers["anomaly_threshold"]:
            return True

    if "kpi_threshold" in triggers:
        # simple example
        return True

    return False


def should_run_scheduled_job(rule: AutomationRule, now: datetime):
    if rule.refresh_frequency == "daily":
        return now.hour == 0

    if rule.refresh_frequency == "weekly":
        return now.weekday() == 0 and now.hour == 0

    if rule.refresh_frequency == "monthly":
        return now.day == 1 and now.hour == 0

    return False


# -----------------------
# Execution
# -----------------------

def run_automation_pipeline(db: Session, dataset_id: int, triggered_by: str):
    history = AutomationRunHistory(
        dataset_id=dataset_id,
        triggered_by=triggered_by,
        status="running",
        started_at=datetime.utcnow()
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    try:
        # Run the full intelligence pipeline
        run_pipeline.delay(dataset_id)

        history.status = "completed"

    except Exception as e:
        history.status = "failed"
        history.error_message = str(e)

    finally:
        history.finished_at = datetime.utcnow()
        db.commit()

        # Trigger notifications AFTER pipeline completes
        run_notifications.delay(dataset_id, triggered_by)

    return history
