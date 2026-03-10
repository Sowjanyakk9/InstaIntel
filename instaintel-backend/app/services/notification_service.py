from datetime import datetime
from sqlalchemy.orm import Session

from app.models.notifications import NotificationRule, NotificationHistory
from app.models.alerts import Alert
from app.models.predictions import Prediction


# -----------------------
# Rule Management
# -----------------------

def create_notification_rule(db: Session, dataset_id: int, data):

    rule = NotificationRule(
        dataset_id=dataset_id,
        notification_enabled=data.notification_enabled,
        channels=data.channels,
        frequency=data.frequency,
        triggers_json=data.triggers_json
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return rule


def update_notification_rule(db: Session, rule: NotificationRule, data):

    for field, value in data.dict(exclude_unset=True).items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)

    return rule


def get_notification_rule(db: Session, dataset_id: int):

    return db.query(NotificationRule).filter(
        NotificationRule.dataset_id == dataset_id
    ).first()


def delete_notification_rule(db: Session, rule: NotificationRule):

    db.delete(rule)
    db.commit()


# -----------------------
# Trigger Evaluation
# -----------------------

def evaluate_notification_triggers(dataset_id, metadata, insights, predictions, alerts, rule):

    triggers = rule.triggers_json or {}

    results = []

    if "risk_threshold" in triggers and predictions:

        if predictions.risk_score > triggers["risk_threshold"]:
            results.append("risk")

    if "alert_threshold" in triggers and alerts:

        if len(alerts) >= triggers["alert_threshold"]:
            results.append("alerts")

    return results


# -----------------------
# Delivery Channels
# -----------------------

def send_email_notification(rule, dataset_id, message):

    # Placeholder for SMTP integration

    print(f"[EMAIL] dataset={dataset_id} message={message}")


def send_slack_notification(rule, dataset_id, message):

    # Placeholder for Slack webhook

    print(f"[SLACK] dataset={dataset_id} message={message}")


def send_teams_notification(rule, dataset_id, message):

    # Placeholder for Teams webhook

    print(f"[TEAMS] dataset={dataset_id} message={message}")


def send_digest_report(dataset_id):

    print(f"[DIGEST] dataset={dataset_id} daily summary")


# -----------------------
# History Logging
# -----------------------

def log_notification_history(db: Session,
                             dataset_id,
                             channel,
                             trigger,
                             content_summary,
                             status,
                             error_message=None):

    record = NotificationHistory(
        dataset_id=dataset_id,
        channel=channel,
        trigger=trigger,
        content_summary=content_summary,
        sent_at=datetime.utcnow(),
        status=status,
        error_message=error_message
    )

    db.add(record)
    db.commit()