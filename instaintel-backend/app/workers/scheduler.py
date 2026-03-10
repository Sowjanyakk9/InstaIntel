from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.models.automation import AutomationRule
from app.services.automation_service import (
    should_run_scheduled_job,
    run_automation_pipeline
)


def check_automation_rules():

    db = SessionLocal()

    rules = db.query(AutomationRule).all()

    now = datetime.utcnow()

    for rule in rules:

        if not rule.automation_enabled:
            continue

        if should_run_scheduled_job(rule, now):

            run_automation_pipeline(
                db,
                rule.dataset_id,
                triggered_by="schedule"
            )

    db.close()


scheduler = BackgroundScheduler()

scheduler.add_job(check_automation_rules, "interval", minutes=5)

scheduler.start()